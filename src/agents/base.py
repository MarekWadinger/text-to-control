import contextlib
import io
import os
import runpy
import shutil
import tempfile
from typing import Any

import google.genai.errors
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from config import Settings

# --- Model setup ---
settings = Settings()
# Default provider using env/config
default_provider = GoogleProvider(api_key=settings.gemini_api_key)

MODEL_PRIORITY = [
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-3-flash-preview",
    "gemini-3-pro-preview",
]


class GeminiFallbackModel(GoogleModel):
    """GoogleModel wrapper with automatic fallback on quota exhaustion."""

    def __init__(self, model_names, provider):
        self.model_names = model_names
        self.current_index = 0
        self.provider = provider
        # initialize the first model
        super().__init__(model_names[self.current_index], provider=provider)

    async def request(
        self, messages, model_settings=None, model_request_parameters=None
    ):
        while self.current_index < len(self.model_names):
            try:
                return await super().request(
                    messages, model_settings, model_request_parameters
                )
            except google.genai.errors.ClientError as e:
                if e.code == 429:
                    print(
                        f"Model {self.model_names[self.current_index]} quota exhausted, switching to next..."
                    )
                    self.current_index += 1
                    if self.current_index < len(self.model_names):
                        self._model_name = self.model_names[self.current_index]
                        continue
                    else:
                        raise RuntimeError(
                            "All Gemini models exhausted, please try again later."
                        )
                else:
                    raise


# Default model instance (using system key)
def get_model(api_key: str | None = None):
    if not api_key:
        return GeminiFallbackModel(MODEL_PRIORITY, default_provider)
    else:
        return GeminiFallbackModel(
            MODEL_PRIORITY, GoogleProvider(api_key=api_key)
        )


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
