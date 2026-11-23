"""Check that the five requested dependencies can be imported."""

import importlib

import pytest


@pytest.mark.parametrize("module_name", ["numpy", "scipy", "cv2", "matplotlib", "pytest"])
def test_dependency_import(module_name):
    module = importlib.import_module(module_name)
    assert module.__version__
