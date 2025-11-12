import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelRetry

from .base import model


@dataclass
class IntegratorDeps:
    """Dependencies used by the IntegratorAgent during code generation."""

    reformulated_text: str | None = None
    expert_assumptions: list[str] = field(default_factory=list)
    generated_code: str | None = None


class IntegratorOutput(BaseModel):
    """Output schema for the IntegratorAgent — generated Python/Pyomo code."""

    code: str


with open("src/instructions/integrator.md", "r", encoding="utf-8") as f:
    integrator_instructions = f.read()


def ruff_check(code: str) -> str:
    """Run Ruff on generated code and auto-fix issues."""
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as tmp:
        tmp.write(code.encode("utf-8"))
        tmp.flush()
        path = tmp.name

    try:
        process = subprocess.run(
            ["uvx", "ruff", "check", "--fix", path],
            capture_output=True,
            text=True,
        )

        output = (process.stdout or "").strip()

        non_fatal_codes = [
            "E741",
            "E722",
            "N802",
            "N803",
            "F841",
            "E402",
            "E305",
            "PLR1722",
            "T201",
            "E0602",
            "PLR2004",
            "F811",
            "E302",
            "N806",
            "ANN001",
            "ANN201",
            "S101",
        ]

        found_codes = re.findall(r"([A-Z]\d{3,4})", output)

        if "All checks passed!" in output or process.returncode == 0:
            print("\n[Ruff] Code passed or auto-fixed successfully.\n")
            with open(path, "r", encoding="utf-8") as f:
                return f.read()

        if found_codes and all(
            code in non_fatal_codes for code in found_codes
        ):
            print(
                f"\n[Ruff] Non-fatal issues found: {found_codes} — proceeding.\n"
            )
            print(output)
            with open(path, "r", encoding="utf-8") as f:
                return f.read()

        raise ModelRetry(
            f"Ruff lint found critical issues that could not be auto-fixed.\n"
            f"Regenerate the code so that it passes Ruff lint cleanly.\n\n"
            f"Ruff output:\n{output}"
        )

    finally:
        if os.path.exists(path):
            os.remove(path)


class IntegratorAgent:
    """Generate runnable code from the ExpertAgent's reformulated problem."""

    def __init__(self):
        """Create the Integrator agent configured to generate and validate code."""
        self.agent = Agent[None, str | IntegratorOutput](
            model,
            deps_type=IntegratorDeps,
            output_type=[ruff_check, IntegratorOutput],
            retries=3,
            instructions=integrator_instructions,
        )


# def ruff_check(code: str) -> str:
#     """Run Ruff on generated code, auto-fix issues, and ignore non-fatal warnings."""
#
#     process = subprocess.run(
#         [
#             "uvx",
#             "ruff",
#             "check",
#             "--fix",
#             "--stdin-filename",
#             "example.py",
#             "-",
#         ],
#         input=code,
#         capture_output=True,
#         text=True,
#     )
#
#     output = (process.stdout or "").strip()
#
#     non_fatal_codes = [
#         "E741",
#         "E722",
#         "N802",
#         "N803",
#         "F841",
#         "E402",
#         "E305",
#         "PLR1722",
#         "T201",
#         "E0602",
#         "PLR2004",
#         "F811",
#         "E302",
#         "N806",
#         "ANN001",
#         "ANN201",
#         "S101",
#     ]
#
#     if "All checks passed!" in output or process.returncode == 0:
#         print("\n[Ruff] Code passed or auto-fixed successfully.\n")
#         return code
#
#     found_codes = re.findall(r"\b([A-Z]+\d+)\b", output)
#
#     if found_codes and all(code in non_fatal_codes for code in found_codes):
#         print(f"\n[Ruff] Non-fatal issues found: {found_codes} — proceeding.\n")
#         print(output)
#         return code
#
#     raise ModelRetry(
#         f"Ruff lint found critical issues that could not be auto-fixed.\n"
#         f"Regenerate the code so that it passes Ruff lint cleanly.\n\n"
#         f"Ruff output:\n{output}"
#     )
