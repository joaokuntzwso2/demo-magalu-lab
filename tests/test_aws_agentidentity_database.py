from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def test_agent_sql_extraction():
    source = (
        ROOT / "scripts/prepare-identity-sql.sh"
    ).read_text()

    assert "identity/agent/postgresql.sql" in source
    assert "identity consent shared agent" in source


def test_agent_database_initialization():
    source = (
        ROOT / "docker/identity-db/init.sh"
    ).read_text()

    assert "wso2_agent" in source

    assert (
        "--dbname wso2_agent "
        "-f /opt/wso2-db-scripts/agent.sql"
    ) in source

    assert (
        "identity.sql consent.sql shared.sql agent.sql"
    ) in source


def test_agent_datasource():
    source = (
        ROOT /
        "docker/wso2/deployment.isolated.template.toml"
    ).read_text()

    source = source.replace(
        "${IS_ADMIN_PASSWORD}", "test-only-admin"
    ).replace(
        "${IS_DB_USER}", "test-only-user"
    ).replace(
        "${IS_DB_PASSWORD}", "test-only-password"
    )

    config = tomllib.loads(source)
    agent = config["datasource"]["AgentIdentity"]

    assert agent["id"] == "AgentIdentity"
    assert agent["url"] == (
        "jdbc:postgresql://identity-db:5432/wso2_agent"
    )
    assert agent["username"] == "test-only-user"
    assert agent["password"] == "test-only-password"
    assert agent["driver"] == "org.postgresql.Driver"
