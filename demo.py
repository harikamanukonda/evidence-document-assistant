"""Reproduce the checked-in example report."""
import json
from pathlib import Path
from core import run
if __name__ == "__main__":
    result = run({})
    target = Path(__file__).parent / "reports/example.json"
    target.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result, indent=2, allow_nan=False))
