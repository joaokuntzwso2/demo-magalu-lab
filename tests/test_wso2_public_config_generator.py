"""Regression test for public WSO2 configuration generation."""

import os
import shutil
import stat
import subprocess
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_public_ip_console_section_order(tmp_path):
    """Parent console section must precede its child scopes section."""

    script_dir = tmp_path / "scripts"
    template_dir = tmp_path / "docker" / "wso2"

    script_dir.mkdir()
    template_dir.mkdir(parents=True)

    shutil.copy2(
        ROOT / "scripts/prepare-wso2-config.py",
        script_dir / "prepare-wso2-config.py",
    )

    shutil.copy2(
        ROOT / "docker/wso2/deployment.isolated.template.toml",
        template_dir / "deployment.isolated.template.toml",
    )

    origin = "https://" + "54.20.194.28"

    env = {
        "PATH": os.environ.get("PATH", ""),
        "MAGALU_ENV_MODE": "isolated",
        "IS_PUBLIC_URL": origin,
        "IS_ADMIN_PASSWORD": "dummy-test-admin",
        "IS_DB_USER": "dummy_test_user",
        "IS_DB_PASSWORD": "dummy-test-db",
    }

    subprocess.run(
        [sys.executable, str(script_dir / "prepare-wso2-config.py")],
        cwd=tmp_path,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    generated = tmp_path / "generated/wso2/deployment.toml"

    content = generated.read_text()
    config = tomllib.loads(content)

    sections = [
        line.strip()
        for line in content.splitlines()
        if line.strip().startswith("[")
        and line.strip().endswith("]")
    ]

    assert sections.count("[console]") == 1
    assert sections.count("[console.flows.scopes]") == 1

    assert sections.index("[console]") < sections.index(
        "[console.flows.scopes]"
    )

    assert config["server"]["hostname"] == "54.20.194.28"
    assert config["server"]["base_path"] == origin

    assert config["console"]["callback_url"] == origin + "/console"
    assert config["myaccount"]["callback_url"] == origin + "/myaccount"

    assert (
        config["transport"]["https"]["properties"]["proxyPort"]
        == 443
    )

    assert "AgentIdentity" in config["datasource"]

    assert stat.S_IMODE(generated.stat().st_mode) == 0o600
