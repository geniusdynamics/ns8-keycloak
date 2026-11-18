#
# Copyright (C) 2026 Nethesis S.r.l.
# Copyright (C) 2026 Genius Dynamics
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""NS8 OIDC provider integration for dedicated, LDAP-backed Keycloak realms."""

import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
from urllib.parse import urlsplit

import agent
from agent.ldapproxy import Ldapproxy
import kcadmin

MODULE_ATTRIBUTE = "ns8.module_id"
REALM_ATTRIBUTE = "ns8.keycloak.user-domain"
LDAP_COMPONENT_NAME = "ns8-ldap"
GROUP_MAPPER_NAME = "ns8-groups"
AUDIENCE_PREFIX = "ns8-audience-"
LDAPPROXY_HOST = "cluster-localnode"
DOMAIN_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9.-]{0,252}")


def validation(field, value, error):
    agent.set_status("validation-failed")
    json.dump([{"field": field, "parameter": field, "value": value, "error": error}], sys.stdout)
    raise SystemExit(2)


def enabled():
    environment = agent.read_envfile(Path(os.environ["AGENT_STATE_DIR"]) / "environment")
    return environment.get("NS8_OIDC_ENABLED", "").lower() == "true"


def lock():
    return agent.exclusive_file_lock(Path(os.environ["AGENT_STATE_DIR"]) / "oidc-realms")


def active():
    return subprocess.run(
        ["systemctl", "--user", "-q", "is-active", "keycloak-app.service"]
    ).returncode == 0


def issuer_prefix():
    return f"https://{os.environ['TRAEFIK_HOST']}/realms/"


def publish(enabled):
    agent_id = os.environ["AGENT_ID"]
    key = f"{agent_id}/srv/http/oidc"
    rdb = agent.redis_connect(privileged=True)
    if enabled:
        record = {"host": os.environ["TRAEFIK_HOST"], "issuer_url_prefix": issuer_prefix()}
        if rdb.hgetall(key) == record:
            return
        rdb.hset(key, mapping=record)
    else:
        if not rdb.delete(key):
            return
        record = {"host": "", "issuer_url_prefix": ""}
    rdb.publish(f"{agent_id}/event/service-oidc-changed", json.dumps({
        **record, "key": key, "module_id": os.environ["MODULE_ID"], "module_uuid": os.environ["MODULE_UUID"],
    }))


def principal(request):
    task_user = os.environ.get("AGENT_TASK_USER", "")
    if task_user:
        if "module_id" in request:
            validation("module_id", request["module_id"], "module_id_not_allowed")
        if not re.fullmatch(r"module/[A-Za-z0-9_.-]+", task_user):
            validation("module_id", task_user, "caller_not_a_module")
        return task_user.removeprefix("module/")
    if not request.get("module_id"):
        validation("module_id", "", "module_id_required")
    return request["module_id"]


def validated_origin(uri, field, *, origin_only=False, logout=False):
    try:
        parsed = urlsplit(uri)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if (
            parsed.scheme not in ("https", "http") or not parsed.hostname
            or not re.fullmatch(r"[A-Za-z0-9.\-:\[\]]+", parsed.netloc)
            or parsed.port == 0 or "\\" in uri or "#" in uri
            or re.search(r"[^\x21-\x7e]", uri)
            or (origin_only and uri != origin)
            or ("*" in uri and not (logout and uri == origin + "/*"))
        ):
            raise ValueError
    except ValueError:
        validation(field, "", "invalid_uri")
    return origin


def ldap_component_config(lp, domain, ldom):
    """Configure a read-only LDAP federation through the local NS8 tunnel."""
    users_clause = lp.get_ldap_users_search_filter_clause(domain)
    config = {
        "enabled": ["true"],
        "editMode": ["READ_ONLY"],
        "connectionUrl": [f"ldap://{LDAPPROXY_HOST}:{ldom['port']}"],
        "authType": ["simple"],
        "bindDn": [ldom["bind_dn"]],
        "bindCredential": [ldom["bind_password"]],
        "importEnabled": ["true"],
        "syncRegistrations": ["false"],
        "trustEmail": ["true"],
        "useTruststoreSpi": ["never"],
        "connectionPooling": ["true"],
    }
    if ldom["schema"] == "ad":
        config.update({
            "vendor": ["ad"],
            "usersDn": [ldom["base_dn"]],
            "searchScope": ["2"],
            "usernameLDAPAttribute": ["sAMAccountName"],
            "rdnLDAPAttribute": ["cn"],
            "uuidLDAPAttribute": ["objectGUID"],
            "userObjectClasses": ["person, organizationalPerson, user"],
            "customUserSearchFilter": [f"(&(objectCategory=person){users_clause})"],
            "pagination": ["true"],
        })
    else:
        config.update({
            "vendor": ["other"],
            "usersDn": [f"ou=People,{ldom['base_dn']}"],
            "searchScope": ["1"],
            "usernameLDAPAttribute": ["uid"],
            "rdnLDAPAttribute": ["uid"],
            "uuidLDAPAttribute": ["entryUUID"],
            "userObjectClasses": ["inetOrgPerson, posixAccount"],
            "customUserSearchFilter": [users_clause],
            "pagination": ["false"],
        })
    return config

def group_mapper_config(lp, domain, ldom):
    config = {
        "group.name.ldap.attribute": ["cn"],
        "groups.ldap.filter": [lp.get_ldap_groups_search_filter_clause(domain)],
        "preserve.group.inheritance": ["false"],
        "mode": ["READ_ONLY"],
        "user.roles.retrieve.strategy": ["LOAD_GROUPS_BY_MEMBER_ATTRIBUTE"],
        "drop.non.existing.groups.during.sync": ["false"],
    }
    if ldom["schema"] == "ad":
        config.update({
            "groups.dn": [ldom["base_dn"]],
            "group.object.classes": ["group"],
            "membership.ldap.attribute": ["member"],
            "membership.attribute.type": ["DN"],
            "membership.user.ldap.attribute": ["cn"],
        })
    else:
        config.update({
            "groups.dn": [f"ou=Groups,{ldom['base_dn']}"],
            "group.object.classes": ["posixGroup"],
            "membership.ldap.attribute": ["memberUid"],
            "membership.attribute.type": ["UID"],
            "membership.user.ldap.attribute": ["uid"],
        })
    return config

def get_realm(kc, domain):
    try:
        return kc.get(f"/{domain}")
    except kcadmin.KeycloakError as error:
        if error.status in (403, 404):
            return None
        raise


def is_managed(realm, domain):
    return (realm or {}).get("attributes", {}).get(REALM_ATTRIBUTE) == domain


def managed_realms(kc):
    try:
        return [
            rep["realm"] for rep in kc.get("", params={"briefRepresentation": "true"})
            if rep["realm"] != "master" and DOMAIN_NAME.fullmatch(rep["realm"])
            and is_managed(get_realm(kc, rep["realm"]), rep["realm"])
        ]
    except kcadmin.KeycloakError as error:
        if error.status == 403:
            return []
        raise


def ensure_component(kc, domain, name, provider, provider_type, parent, config):
    path = f"/{domain}/components"
    components = kc.get(path, params={"parent": parent, "type": provider_type})
    existing = next((item for item in components if item["name"] == name), None)
    if existing:
        if existing["providerId"] != provider:
            raise RuntimeError(f"Keycloak component {name} has a different provider")
        if any(existing["config"].get(key) != value for key, value in config.items()):
            existing["config"].update(config)
            kc.put(f"{path}/{existing['id']}", existing)
        return existing["id"]
    location = kc.post(path, {
        "name": name, "providerId": provider, "providerType": provider_type,
        "parentId": parent, "config": config,
    })
    return location.rstrip("/").rsplit("/", 1)[-1]


def update_ldap(kc, domain, realm, lp, ldap):
    ldap_id = ensure_component(
        kc, domain, LDAP_COMPONENT_NAME, "ldap", "org.keycloak.storage.UserStorageProvider",
        realm["id"], ldap_component_config(lp, domain, ldap),
    )
    ensure_component(
        kc, domain, GROUP_MAPPER_NAME, "group-ldap-mapper",
        "org.keycloak.storage.ldap.mappers.LDAPStorageMapper", ldap_id,
        group_mapper_config(lp, domain, ldap),
    )


def ensure_realm(kc, domain, lp, ldap):
    realm = get_realm(kc, domain)
    if realm is None:
        try:
            kc.post("", {
                "realm": domain, "displayName": domain, "enabled": True,
                "registrationAllowed": False, "attributes": {REALM_ATTRIBUTE: domain},
            })
        except kcadmin.KeycloakError as error:
            if error.status == 409:
                validation("domain", domain, "realm_name_already_used")
            raise
        kc.renew_token()
        realm = get_realm(kc, domain)
    if not is_managed(realm, domain):
        validation("domain", domain, "realm_name_already_used")
    update_ldap(kc, domain, realm, lp, ldap)


def audience_mapper(client_id):
    return {
        "name": AUDIENCE_PREFIX + client_id,
        "protocol": "openid-connect",
        "protocolMapper": "oidc-audience-mapper",
        "config": {
            "included.client.audience": client_id,
            "access.token.claim": "true",
            "id.token.claim": "false",
            "introspection.token.claim": "true",
        },
    }


def update_audience(kc, path, requested):
    desired = {AUDIENCE_PREFIX + client: audience_mapper(client) for client in requested}
    models = path + "/protocol-mappers/models"
    for existing in kc.get(models):
        name = existing["name"]
        if not name.startswith(AUDIENCE_PREFIX) or existing["protocolMapper"] != "oidc-audience-mapper":
            continue
        if name not in desired:
            kc.delete(f"{models}/{existing['id']}")
        else:
            target = desired.pop(name)
            if existing["config"] != target["config"]:
                kc.put(f"{models}/{existing['id']}", {**target, "id": existing["id"]})
    for mapper in desired.values():
        kc.post(models, mapper)


def ensure_client(kc, domain, module_id, request, logout):
    redirects = request.get("redirect_uris", [])
    current = kc.find_client(domain, module_id)
    if current is not None and (current.get("attributes") or {}).get(MODULE_ATTRIBUTE) != module_id:
        validation("module_id", module_id, "client_id_already_used")
    attributes = {
        **((current or {}).get("attributes") or {}),
        MODULE_ATTRIBUTE: module_id, "post.logout.redirect.uris": "##".join(logout),
        "oauth2.device.authorization.grant.enabled": "false", "oidc.ciba.grant.enabled": "false",
    }
    settings = {
        "clientId": module_id, "name": module_id,
        "protocol": "openid-connect", "publicClient": False,
        "clientAuthenticatorType": "client-secret",
        "standardFlowEnabled": bool(redirects), "implicitFlowEnabled": False,
        "directAccessGrantsEnabled": False, "serviceAccountsEnabled": False,
        "redirectUris": redirects, "webOrigins": request.get("web_origins", []),
        "attributes": attributes,
    }
    audience = request.get("audience", [])
    clients = f"/{domain}/clients"
    if current is None:
        secret = secrets.token_urlsafe(32)
        kc.post(clients, {
            **settings, "enabled": True, "secret": secret,
            "protocolMappers": [audience_mapper(client) for client in audience],
        })
        return secret

    path = f"{clients}/{current['id']}"
    current.pop("secret", None)
    current.pop("protocolMappers", None)
    kc.put(path, {**current, **settings})
    update_audience(kc, path, audience)
    secret_path = path + "/client-secret"
    secret = kc.post(secret_path) if request.get("rotate_secret") else kc.get(secret_path)
    return secret["value"]


def register(request):
    module_id = principal(request)
    domain = request["domain"]
    if not DOMAIN_NAME.fullmatch(domain) or domain.lower() == "master":
        validation("domain", domain, "invalid_user_domain")
    origins = {validated_origin(uri, "redirect_uris") for uri in request.get("redirect_uris", [])}
    logout = request.get("post_logout_redirect_uris", [f"{origin}/*" for origin in sorted(origins)])
    for uri in logout:
        validated_origin(uri, "post_logout_redirect_uris", logout=True)
    for origin in request.get("web_origins", []):
        validated_origin(origin, "web_origins", origin_only=True)

    with lock():
        rdb = agent.redis_connect()
        if domain not in agent.get_bound_domain_list(rdb, module_id):
            validation("domain", domain, "domain_not_bound_to_module")
        if not enabled() or not kcadmin.secret_path().exists() or not active():
            validation("domain", domain, "ns8_sso_unavailable")
        lp = Ldapproxy()
        ldap = lp.get_domain(domain)
        if ldap is None or ldap["schema"] not in ("rfc2307", "ad"):
            validation("domain", domain, "unsupported_user_domain")
        kc = kcadmin.agent_client()
        ensure_realm(kc, domain, lp, ldap)
        bound = agent.get_bound_domain_list(rdb)
        if domain not in bound:
            agent.bind_user_domains([*bound, domain], check=True)
        secret = ensure_client(kc, domain, module_id, request, logout)

    return {"client_id": module_id, "client_secret": secret, "realm": domain, "issuer": issuer_prefix() + domain}


def reconcile():
    if not enabled() or not kcadmin.secret_path().exists():
        return
    with lock():
        if not enabled():
            return
        kc = kcadmin.agent_client()
        kcadmin.wait_ready(timeout=120)
        rdb = agent.redis_connect()
        lp = Ldapproxy()
        for domain in managed_realms(kc):
            ldap = lp.get_domain(domain)
            if ldap is not None:
                update_ldap(kc, domain, get_realm(kc, domain), lp, ldap)
            for client in kc.get(f"/{domain}/clients"):
                owner = (client.get("attributes") or {}).get(MODULE_ATTRIBUTE)
                if owner and (ldap is None or domain not in agent.get_bound_domain_list(rdb, owner)):
                    kc.delete(f"/{domain}/clients/{client['id']}")
        publish(True)
