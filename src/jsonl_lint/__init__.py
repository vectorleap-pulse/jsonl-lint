"""Zero-dependency validator for JSONL files."""

from jsonl_lint.core import BOM, Problem, Report, check, iter_problems, load

__all__ = ["BOM", "Problem", "Report", "check", "iter_problems", "load"]
__version__ = "0.1.0"
