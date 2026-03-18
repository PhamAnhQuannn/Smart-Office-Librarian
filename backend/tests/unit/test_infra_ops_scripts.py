from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = ROOT / "infra" / "scripts"

OPS_SCRIPT_NAMES = (
    "common.sh",
    "deploy.sh",
    "rollback.sh",
    "health_check.sh",
    "db_migrate.sh",
    "restart_services.sh",
    "scale_workers.sh",
    "logs.sh",
)


def _read_script(name: str) -> str:
    path = SCRIPTS_DIR / name
    return path.read_text(encoding="utf-8")


def test_ops_scripts_are_non_placeholder_and_hardened() -> None:
    for script_name in OPS_SCRIPT_NAMES:
        content = _read_script(script_name)
        assert content.strip(), f"{script_name} must not be empty"
        assert content.startswith("#!/usr/bin/env bash"), f"{script_name} must use bash"
        assert "set -euo pipefail" in content, f"{script_name} should fail fast"


def test_deploy_and_rollback_scripts_track_release_metadata() -> None:
    deploy_content = _read_script("deploy.sh")
    rollback_content = _read_script("rollback.sh")

    assert "current_release_" in deploy_content
    assert "deploy_history.log" in deploy_content
    assert "health_check.sh" in deploy_content
    assert "db_migrate.sh" in deploy_content

    assert "target-release" in rollback_content
    assert "rollback_history.log" in rollback_content
    assert "current_release_" in rollback_content


def test_health_check_has_required_endpoint_defaults() -> None:
    content = _read_script("health_check.sh")

    assert "API_HEALTH_URL" in content
    assert "API_READY_URL" in content
    assert "METRICS_URL" in content
    assert "FRONTEND_URL" in content


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash is required for syntax checks")
def test_ops_scripts_have_valid_bash_syntax() -> None:
    for script_name in OPS_SCRIPT_NAMES:
        script_path = SCRIPTS_DIR / script_name
        result = subprocess.run(
            ["bash", "-n", str(script_path)],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"bash -n failed for {script_name}: {result.stdout}\n{result.stderr}"
        )
