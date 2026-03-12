#!/usr/bin/env python3
"""
Compatibility bridge for n8n hotspot workflows.

This wraps the repo-local n8n_hotspot_workflow.py entrypoint so older workflow
configs can keep using the "bridge" name without depending on external
~/.openclaw paths.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_main():
    workflow_path = Path(__file__).with_name("n8n_hotspot_workflow.py")
    spec = importlib.util.spec_from_file_location("n8n_hotspot_workflow", workflow_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load workflow module: {workflow_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.main


if __name__ == "__main__":
    main = _load_main()
    sys.exit(main())
