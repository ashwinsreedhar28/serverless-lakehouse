"""One connection factory for every Snowflake step. Key-pair auth, because trial accounts enforce MFA on
password logins, which an unattended loader or dbt cannot answer.

Configuration comes from the environment (snowflake/.env is read if present; it is gitignored — *.env never commits):

    SNOWFLAKE_ACCOUNT        e.g. abc12345.us-east-1  (or the org-account form: myorg-myaccount)
    SNOWFLAKE_USER
    SNOWFLAKE_PRIVATE_KEY_PATH   default ~/.snowflake/lakehouse_rsa_key.p8
    SNOWFLAKE_PRIVATE_KEY_PASSPHRASE   optional
    SNOWFLAKE_ROLE           default LAKEHOUSE_ROLE
    SNOWFLAKE_WAREHOUSE      default LAKEHOUSE_WH
    SNOWFLAKE_DATABASE       default LAKEHOUSE

The dbt profile (snowflake/dbt/profiles.yml) reads the same variables, so one .env drives both.
"""

from __future__ import annotations

import os
from pathlib import Path

from ..config import REPO_ROOT

ENV_FILE = REPO_ROOT / "snowflake" / ".env"

DEFAULTS = {
    "SNOWFLAKE_ROLE": "LAKEHOUSE_ROLE",
    "SNOWFLAKE_WAREHOUSE": "LAKEHOUSE_WH",
    "SNOWFLAKE_DATABASE": "LAKEHOUSE",
    "SNOWFLAKE_PRIVATE_KEY_PATH": str(Path.home() / ".snowflake" / "lakehouse_rsa_key.p8"),
}


def load_env(path: Path = ENV_FILE) -> dict[str, str]:
    """KEY=value lines → os.environ (existing variables win). Returns the effective config."""
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    cfg = {k: os.environ.get(k, d) for k, d in DEFAULTS.items()}
    for k in ("SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER"):
        if not os.environ.get(k):
            raise SystemExit(f"{k} is not set; copy snowflake/.env.example to snowflake/.env and fill it in")
        cfg[k] = os.environ[k]
    cfg["SNOWFLAKE_PRIVATE_KEY_PASSPHRASE"] = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE", "")
    return cfg


def private_key_bytes(cfg: dict[str, str]) -> bytes:
    from cryptography.hazmat.primitives import serialization

    p = Path(cfg["SNOWFLAKE_PRIVATE_KEY_PATH"]).expanduser()
    if not p.is_file():
        raise SystemExit(f"private key not found at {p}; see snowflake/README.md → key-pair auth")
    pw = cfg["SNOWFLAKE_PRIVATE_KEY_PASSPHRASE"].encode() or None
    key = serialization.load_pem_private_key(p.read_bytes(), password=pw)
    return key.private_bytes(encoding=serialization.Encoding.DER,
                             format=serialization.PrivateFormat.PKCS8,
                             encryption_algorithm=serialization.NoEncryption())


def connect(schema: str = "BRONZE", *, role: str | None = None):
    import snowflake.connector

    cfg = load_env()
    return snowflake.connector.connect(
        account=cfg["SNOWFLAKE_ACCOUNT"], user=cfg["SNOWFLAKE_USER"],
        private_key=private_key_bytes(cfg),
        role=role or cfg["SNOWFLAKE_ROLE"], warehouse=cfg["SNOWFLAKE_WAREHOUSE"],
        database=cfg["SNOWFLAKE_DATABASE"], schema=schema,
        session_parameters={"TIMEZONE": "UTC", "QUERY_TAG": "serverless-lakehouse"},
        client_session_keep_alive=False,
    )


def run(cur, sql: str, params=None):
    """Execute and return all rows. Thin wrapper so every statement goes through one place (easy to log)."""
    if os.environ.get("SF_ECHO"):
        print("  sql>", " ".join(sql.split())[:300])
    cur.execute(sql, params)
    return cur.fetchall()
