from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_ldap_persistent_volumes():
    data = yaml.safe_load(
        (ROOT / "compose.stores.yaml").read_text()
    )

    ldap = data["services"]["ldap"]
    mounts = ldap["volumes"]

    assert "ldap-data:/var/lib/ldap" in mounts
    assert "ldap-config:/etc/ldap/slapd.d" in mounts

    assert "ldap-data" in data["volumes"]
    assert "ldap-config" in data["volumes"]


def test_ldap_not_publicly_exposed():
    data = yaml.safe_load(
        (ROOT / "compose.stores.yaml").read_text()
    )

    ldap = data["services"]["ldap"]

    assert ldap["ports"] == [
        "127.0.0.1:1389:389"
    ]


def test_private_generated_seed_is_used():
    data = yaml.safe_load(
        (ROOT / "compose.stores.yaml").read_text()
    )

    mounts = data["services"]["ldap"]["volumes"]

    assert any(
        mount.startswith(
            "./generated/poc-ldap/50-seller.ldif:"
        )
        for mount in mounts
    )
