#
# Copyright (C) 2026 Genius Dynamics
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""Provision the Keycloak service account used by NS8 client registration."""

import json
import os
from pathlib import Path
import secrets
import subprocess
import sys

import agent
import kcadmin
import keycloak_oidc as oidc

TEMP_PREFIX = "ns8-keycloak-bootstrap-"
AGENT_MARKER = "ns8.keycloak.module-agent"


def bootstrap_path():
    return Path(os.environ["AGENT_STATE_DIR"]) / "oidc-bootstrap.json"


def seed_temporary_client():
    path = bootstrap_path()
    if not path.exists():
        return
    credentials = json.loads(path.read_text())
    passwords = path.with_name("passwords.env")
    pod = Path(os.environ["XDG_RUNTIME_DIR"]) / "keycloak.pod-id"
    subprocess.run([
        "podman", "run", "--rm", "--pod-id-file", str(pod),
        "--env-file", str(passwords), "--env", "KC_NS8_TEMP_SECRET",
        "--env", "KC_DB=postgres",
        "--env", "KC_DB_URL=jdbc:postgresql://127.0.0.1:5432/keycloak",
        "--env", "KC_DB_USERNAME=keycloak",
        os.environ["KEYCLOAK_IMAGE"],
        "bootstrap-admin", "service", f"--client-id={credentials['id']}",
        "--client-secret:env=KC_NS8_TEMP_SECRET",
    ], env={**os.environ, "KC_NS8_TEMP_SECRET": credentials["secret"]},
        stdout=sys.stderr, timeout=180, check=True)


def bootstrap():
    # Seed the temporary account after PostgreSQL starts and before Keycloak
    # opens the database. This also works after the original admin was removed.
    client_id = TEMP_PREFIX + secrets.token_hex(8)
    client_secret = secrets.token_urlsafe(32)
    path = bootstrap_path()
    fd = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump({"id": client_id, "secret": client_secret}, stream)
        subprocess.run([
            "systemctl", "--user", "restart",
            "keycloak.service", "postgresql-app.service", "keycloak-app.service",
        ], check=True, stdout=sys.stderr)
        kcadmin.wait_ready(timeout=180)
        admin = kcadmin.Client(client_id, client_secret)
        admin.token()
        try:
            create_agent_client(admin)
        finally:
            remove_temporary_clients(admin)
    finally:
        path.unlink(missing_ok=True)


def create_agent_client(admin):
    rep = admin.find_client("master", kcadmin.AGENT_CLIENT_ID)
    if rep is not None and (rep.get("attributes") or {}).get(AGENT_MARKER) != "true":
        raise RuntimeError(f"Keycloak client {kcadmin.AGENT_CLIENT_ID} already exists")
    secret = secrets.token_urlsafe(32)
    update = {
        "clientId": kcadmin.AGENT_CLIENT_ID,
        "name": "NS8 module registration agent",
        "protocol": "openid-connect",
        "clientAuthenticatorType": "client-secret",
        "publicClient": False,
        "serviceAccountsEnabled": True,
        "standardFlowEnabled": False,
        "directAccessGrantsEnabled": False,
        "implicitFlowEnabled": False,
        "enabled": True,
        "secret": secret,
        "attributes": {AGENT_MARKER: "true"},
    }
    clients = "/master/clients"
    if rep is None:
        admin.post(clients, update)
        rep = admin.find_client("master", kcadmin.AGENT_CLIENT_ID)
    else:
        admin.put(f"{clients}/{rep['id']}", {**rep, **update})
    user = admin.get(f"{clients}/{rep['id']}/service-account-user")
    admin.post(f"/master/users/{user['id']}/role-mappings/realm", [
        admin.get("/master/roles/create-realm"),
    ])

    # Restore access only to realms managed by this integration if the local
    # credential was lost. Other realms remain outside the service account.
    for domain in oidc.managed_realms(admin):
        management = admin.find_client("master", domain + "-realm")
        if management:
            admin.post(f"/master/users/{user['id']}/role-mappings/clients/{management['id']}", [
                admin.get(f"{clients}/{management['id']}/roles/realm-admin"),
            ])
    kcadmin.Client(kcadmin.AGENT_CLIENT_ID, secret).token()
    kcadmin.save_agent_secret(secret)


def remove_temporary_clients(admin):
    # Delete the current account last so it can clean up an interrupted run.
    temporary = [
        rep for rep in admin.get("/master/clients", params={"clientId": TEMP_PREFIX, "search": "true"})
        if rep["clientId"].startswith(TEMP_PREFIX)
    ]
    for rep in sorted(temporary, key=lambda rep: rep["clientId"] == admin.client_id):
        admin.delete(f"/master/clients/{rep['id']}")


def configure(enable):
    with oidc.lock():
        if not enable and not oidc.enabled():
            return
        if not oidc.active():
            oidc.validation("enabled", enable, "keycloak_not_running")

        if enable:
            if not os.environ.get("TRAEFIK_HOST") or os.environ.get("TRAEFIK_HTTP2HTTPS", "").lower() != "true":
                oidc.validation("enabled", enable, "https_required")
            if not kcadmin.secret_path().exists():
                bootstrap()
            kcadmin.agent_client().token()
            agent.set_env("NS8_OIDC_ENABLED", True)
            oidc.publish(True)
        else:
            kc = kcadmin.agent_client()
            for realm in oidc.managed_realms(kc):
                for client in kc.get(f"/{realm}/clients"):
                    if (client.get("attributes") or {}).get(oidc.MODULE_ATTRIBUTE) == client["clientId"]:
                        kc.delete(f"/{realm}/clients/{client['id']}")
            agent.set_env("NS8_OIDC_ENABLED", False)
            oidc.publish(False)
