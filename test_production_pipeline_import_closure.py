"""Static import-closure guard for the production pipeline.

Importing the module must resolve its committed production dependencies without
starting a runtime, writing to the database, or submitting an exchange order.
"""

import importlib


def test_production_pipeline_import_closure_is_complete():
    pipeline = importlib.import_module("arunda_pipeline")
    assert callable(pipeline.main)
    assert pipeline.EXECUTION_ENABLED is False
