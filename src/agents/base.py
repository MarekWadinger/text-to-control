import contextlib
import io
import os
import runpy
import shutil
import tempfile
from typing import Any

from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from config import Settings

settings = Settings()
default_provider = OpenAIProvider(api_key=settings.openai_api_key)


def get_model(api_key: str | None = None, model_name: str = "gpt-5.4"):
    provider = OpenAIProvider(api_key=api_key) if api_key else default_provider
    return OpenAIModel(model_name=model_name, provider=provider)


def safe_execute_python_code(code: str) -> dict[str, Any]:
    """Safely execute code (e.g. Pyomo model) in an isolated temp directory."""
    code = code.replace("control.pole(", "control.poles(")
    code = code.replace("ctrl.pole(", "ctrl.poles(")
    code = code.replace("np.trapz(", "np.trapezoid(")
    code = code.replace("spi.simps(", "np.trapezoid(")
    code = code.replace("scipy.integrate.simps(", "np.trapezoid(")
    output_capture = io.StringIO()
    tmp_dir = tempfile.mkdtemp(prefix="sandbox_")
    script_path = os.path.join(tmp_dir, "model.py")
    result: dict[str, Any] = {}

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(code)

    try:
        with contextlib.redirect_stdout(output_capture):
            ns = runpy.run_path(script_path)

            solve_fn = ns.get("solve_model")
            if solve_fn and callable(solve_fn):
                solve_fn()

        result["stdout"] = output_capture.getvalue()
        result["error"] = None

        model_obj = ns.get("model")
        if model_obj:
            try:
                from pyomo.core import Objective

                objs = [
                    c
                    for c in model_obj.component_objects(
                        Objective, active=True
                    )
                ]
                if objs:
                    obj = objs[0]
                    val = obj()
                    result["objective_name"] = obj.name
                    result["objective_value"] = float(val)
            except Exception:
                result["objective_value"] = "Unknown (not solved)"

    except Exception as e:
        result["stdout"] = output_capture.getvalue()
        result["error"] = str(e)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return result
