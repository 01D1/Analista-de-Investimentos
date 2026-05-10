"""
Tests for FOUND-01: canonical src/ imports work; sys.path hacks removed.
All imports must resolve via 'src.' prefix, not via sys.path manipulation.
"""
import ast
import pytest
from pathlib import Path


def test_src_utils_importable():
    """src.utils modules import without sys.path manipulation."""
    from src.utils.retry import retry
    from src.utils.logger import get_logger, configure_logging
    assert callable(retry)
    assert callable(get_logger)


def test_config_settings_importable():
    """config.settings resolves from project root."""
    from config.settings import settings
    assert settings is not None


def test_no_sys_path_manipulation_in_pipeline():
    """src/processing/pipeline.py no longer uses sys.path.insert/append."""
    pipeline_src = (
        Path(__file__).parent.parent / "src" / "processing" / "pipeline.py"
    )
    tree = ast.parse(pipeline_src.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            if (
                isinstance(node.value, ast.Name)
                and node.value.id == "sys"
                and node.attr == "path"
            ):
                pytest.fail(
                    f"sys.path manipulation found in pipeline.py at line {node.lineno}. "
                    "Remove it and use src. prefix imports."
                )
