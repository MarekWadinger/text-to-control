import contextlib
import io
import os
import runpy
import shutil
import tempfile
from typing import Any

from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from config import Settings

# --- Model setup ---
settings = Settings()
provider = GoogleProvider(api_key=settings.gemini_api_key)
model = GoogleModel("gemini-flash-lite-latest", provider=provider)


def safe_execute_python_code(code: str) -> dict[str, Any]:
    """Safely execute Python code (e.g. Pyomo model) in an isolated temp directory."""
    from typing import Any

    output_capture = io.StringIO()
    tmp_dir = tempfile.mkdtemp(prefix="sandbox_")
    script_path = os.path.join(tmp_dir, "model.py")
    result: dict[str, Any] = {}

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(code)

    try:
        with contextlib.redirect_stdout(output_capture):
            ns = runpy.run_path(script_path)

            for name, fn in ns.items():
                if callable(fn) and "solve" in name.lower():
                    fn()
                    break
            else:
                pass

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
