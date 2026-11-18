#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Test the OIDC flow on the QEMU node with an NS8 LDAP user."""

import base64
from html.parser import HTMLParser
from http.client import HTTPSConnection
from http.cookies import SimpleCookie
import json
import ssl
import sys
from urllib.parse import parse_qs, urlencode, urlsplit


class LoginForm(HTMLParser):
    def __init__(self):
        super().__init__()
        self.action = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form" and attrs.get("id") == "kc-form-login":
            self.action = attrs["action"]


def check(host, domain, username, password, client):
    issuer = f"https://{host}/realms/{domain}"
    redirect = "https://app.keycloak-ci.test/callback"
    cookies = SimpleCookie()

    def request(method, url, form=None):
        parsed = urlsplit(url)
        assert parsed.scheme == "https" and parsed.netloc == host
        path = parsed.path + ("?" + parsed.query if parsed.query else "")
        headers = {"Host": host, "Cookie": "; ".join(m.OutputString().split(";", 1)[0] for m in cookies.values())}
        body = None
        if form is not None:
            body = urlencode(form)
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        # The test node uses a local Traefik certificate.
        conn = HTTPSConnection("127.0.0.1", timeout=10, context=ssl._create_unverified_context())
        try:
            conn.request(method, path, body, headers)
            response = conn.getresponse()
            for name, value in response.getheaders():
                if name.lower() == "set-cookie":
                    cookies.load(value)
            return response.status, response.getheader("Location"), response.read().decode()
        finally:
            conn.close()

    status, _, body = request("GET", issuer + "/.well-known/openid-configuration")
    assert status == 200, f"Discovery status {status}"
    metadata = json.loads(body)
    assert metadata["issuer"] == issuer
    authorize = metadata["authorization_endpoint"] + "?" + urlencode({
        "client_id": client["client_id"], "redirect_uri": redirect, "response_type": "code",
        "scope": "openid profile", "state": "keycloak-ci", "nonce": "keycloak-ci",
    })
    status, location, body = request("GET", authorize)
    for _ in range(4):
        if status not in (302, 303):
            break
        status, location, body = request("GET", location)
    assert status == 200, f"Login form status {status}"
    parser = LoginForm()
    parser.feed(body)
    assert parser.action, "Missing Keycloak login form"
    status, location, _ = request("POST", parser.action, {"username": username, "password": password})
    assert status in (302, 303), f"LDAP sign-in status {status}"
    callback = urlsplit(location)
    assert callback.hostname == "app.keycloak-ci.test" and callback.path == "/callback"
    result = parse_qs(callback.query)
    assert result.get("state") == ["keycloak-ci"] and "code" in result, "Missing authorization code"
    status, _, body = request("POST", metadata["token_endpoint"], {
        "grant_type": "authorization_code", "client_id": client["client_id"],
        "client_secret": client["client_secret"], "code": result["code"][0], "redirect_uri": redirect,
    })
    assert status == 200, f"Token exchange status {status}"
    tokens = json.loads(body)
    for name in ("id_token", "access_token"):
        payload = tokens[name].split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        assert claims["iss"] == issuer and claims["preferred_username"] == username


if __name__ == "__main__":
    check(*sys.argv[1:], json.load(sys.stdin))
