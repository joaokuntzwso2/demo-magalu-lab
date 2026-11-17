import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/prepare-wso2-config.py"
TEMPLATE = ROOT / "docker/wso2/deployment.isolated.template.toml"


def render(tmp_path, public_url):
    folder = tmp_path / "docker/wso2"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / TEMPLATE.name).write_bytes(TEMPLATE.read_bytes())

    env = os.environ.copy()
    env.update({
        "MAGALU_ENV_MODE": "isolated",
        "IS_PUBLIC_URL": public_url,
        "IS_ADMIN_PASSWORD": "synthetic-test-only",
        "IS_DB_USER": "wso2",
        "IS_DB_PASSWORD": "synthetic-db-test-only",
    })

    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )

    target = tmp_path / "generated/wso2/deployment.toml"
    return result, target


def test_local_configuration_is_preserved(tmp_path):
    result, target = render(
        tmp_path, "https://localhost:9543"
    )
    assert result.returncode == 0, result.stderr

    config = tomllib.loads(target.read_text())
    assert config["server"]["hostname"] == "localhost"
    assert "carbon.management.port" in config["server"]["base_path"]


def test_aws_configuration(tmp_path):
    result, target = render(
        tmp_path, "https://auth.example.test"
    )
    assert result.returncode == 0, result.stderr

    config = tomllib.loads(target.read_text())

    assert config["server"]["hostname"] == "auth.example.test"
    assert config["server"]["base_path"] == "https://auth.example.test"

    assert config["transport"]["https"]["properties"]["proxyPort"] == 443

    assert config["console"]["callback_url"] == (
        "https://auth.example.test/console"
    )

    assert config["myaccount"]["callback_url"] == (
        "https://auth.example.test/myaccount"
    )


@pytest.mark.parametrize("url", [
    "http://auth.example.test",
    "https://auth.example.test:9543",
    "https://auth.example.test/console",
])
def test_invalid_public_origins_are_rejected(tmp_path, url):
    result, target = render(tmp_path, url)
    assert result.returncode != 0
    assert not target.exists()
