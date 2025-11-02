"""
Purpose: Extract validated task instances from validation logs without creating GitHub branches.

This is a simplified version of gather.py that:
- Reads validation reports
- Filters for valid instances (has F2P and P2P tests)
- Saves task instances JSON without git operations

Usage: python -m swesmith.harness.simple_gather logs/run_validation/<run_id>
"""

import argparse
import json
import os

from pathlib import Path
from swebench.harness.constants import (
    FAIL_TO_PASS,
    PASS_TO_PASS,
    KEY_INSTANCE_ID,
    LOG_REPORT,
)
from swesmith.constants import (
    KEY_PATCH,
    KEY_TIMED_OUT,
    LOG_DIR_RUN_VALIDATION,
    LOG_DIR_TASKS,
    REF_SUFFIX,
)


def main(validation_logs_path: str | Path) -> None:
    """
    Extract validated task instances from validation logs.

    Args:
        validation_logs_path: Path to the validation logs directory
    """
    validation_logs_path = Path(validation_logs_path)
    
    # Validate path
    if not validation_logs_path.exists():
        raise FileNotFoundError(
            f"Validation logs path {validation_logs_path} does not exist"
        )
    if not validation_logs_path.is_dir():
        raise ValueError(
            f"Validation logs path {validation_logs_path} is not a directory"
        )
    
    run_id = validation_logs_path.name
    task_instances_path = LOG_DIR_TASKS / f"{run_id}.json"
    
    print(f"Extracting task instances from {validation_logs_path}")
    print(f"Output path: {task_instances_path}")
    
    task_instances = []
    
    for folder in sorted(validation_logs_path.iterdir()):
        if not folder.is_dir() or folder.name.endswith(REF_SUFFIX):
            continue
        
        report_path = folder / LOG_REPORT
        patch_path = folder / "patch.diff"
        
        if not report_path.exists():
            print(f"Skipping {folder.name}: No report found")
            continue
        
        if not patch_path.exists():
            print(f"Skipping {folder.name}: No patch found")
            continue
        
        with open(report_path) as f:
            report = json.load(f)
        
        # Check if valid (has F2P and P2P, no timeout, no collection errors)
        f2p = report.get(FAIL_TO_PASS, [])
        p2p = report.get(PASS_TO_PASS, [])
        
        if KEY_TIMED_OUT in report:
            print(f"Skipping {folder.name}: Timed out")
            continue
        
        if report.get("collection_errors", False):
            print(f"Skipping {folder.name}: Collection errors (too broken)")
            continue
        
        if len(f2p) == 0:
            print(f"Skipping {folder.name}: No FAIL_TO_PASS tests")
            continue
        
        if len(p2p) == 0:
            print(f"Skipping {folder.name}: No PASS_TO_PASS tests")
            continue
        
        with open(patch_path) as f:
            patch_content = f.read()
        
        task_instance = {
            KEY_INSTANCE_ID: folder.name,
            KEY_PATCH: patch_content,
            FAIL_TO_PASS: f2p,
            PASS_TO_PASS: p2p,
            "repo": run_id,  # Use run_id as repo identifier
        }
        
        task_instances.append(task_instance)
        print(f"✓ Added {folder.name}: {len(f2p)} F2P, {len(p2p)} P2P")
    
    # Save to file
    task_instances_path.parent.mkdir(parents=True, exist_ok=True)
    with open(task_instances_path, "w") as f:
        json.dump(task_instances, f, indent=4)
    
    print(f"\n✓ Saved {len(task_instances)} task instances to {task_instances_path}")
    print(f"  - {len(task_instances)} valid instances")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract validated task instances from validation logs (without git operations)"
    )
    parser.add_argument(
        "validation_logs_path",
        type=str,
        help="Path to the validation logs directory (e.g., logs/run_validation/pandas-dev__pandas.8f359f8e)",
    )
    args = parser.parse_args()
    main(args.validation_logs_path)

