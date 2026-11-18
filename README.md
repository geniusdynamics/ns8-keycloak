# ns8-keycloak

Open source identity and access management with single sign-on, OpenID Connect and SAML, backed by PostgreSQL.

Module id: `keycloak`. Images are pinned in `build-images.sh` and updated through reviewed changes.

## Install

```bash
add-module ghcr.io/geniusdynamics/keycloak:latest 1
```

The command returns the instance id, for example `keycloak1`. Use the id NS8 returns.

## Configure

```bash
api-cli run configure-module --agent module/keycloak1 --data - <<'EOF'
{
  "host": "keycloak.example.org"
}
EOF
```

| Parameter | Required | Type | Description |
|---|---|---|---|
| `host` | yes | string | Host name for the application, like 'keycloak.example.org' |
| `lets_encrypt` | no | boolean | Request a valid Let's Encrypt certificate. |
| `http2https` | no | boolean | Redirect all the HTTP requests to HTTPS |

## Configuration output

`get-configuration` returns: `host`, `lets_encrypt`, `http2https`.

## Images

| Image | Version |
|---|---|
| `docker.io/postgres` | `18.7-alpine3.24` |
| `quay.io/keycloak/keycloak` | `26.8.2` |

Requires NS8 core `3.20.1` or newer.

## Network and access

- Reserves 1 TCP port(s) on the node. The web application is published through Traefik on the configured host name.
- Runs rootless.
- Declares these NS8 authorizations: `traefik@node:routeadm` and `cluster:accountconsumer`.

## Backup

The following paths are included in the NS8 backup (`imageroot/etc/state-include.conf`):

- `state/passwords.env`
- `state/keycloak.pg_dump`

## Services

- `keycloak-app.service`
- `keycloak.service`
- `postgresql-app.service`

## Get the configuration

```bash
api-cli run get-configuration --agent module/keycloak1
```

## Update and uninstall

```bash
api-cli run update-module --data '{"module_url":"ghcr.io/geniusdynamics/keycloak:latest","instances":["keycloak1"],"force":true}'
remove-module --no-preserve keycloak1
```

## Testing

Continuous integration:

- `Publish images` builds the module image on every push.
- `Test module` installs the image on a QEMU NS8 node and runs the Robot Framework suite in `tests/`. It runs after `Publish images` succeeds on `dev` and on `main`.
- `Build API JSON Schema docs` and the security scan run alongside.

The suite installs the module, configures a host name, checks that the web application answers through Traefik, takes UI screenshots and removes the module.

Run it locally with the NS8 standard infrastructure described in the [ns8-github-actions README](https://github.com/NethServer/ns8-github-actions/blob/v1/README.md#running-tests-locally).

## Upstream

Application documentation: https://www.keycloak.org/documentation

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).

## NS8 single sign-on

The optional NS8 OIDC provider gives each user domain its own Keycloak realm
with read-only LDAP federation. It leaves existing realms and clients alone.
If a manually managed realm already uses a domain's name, Keycloak rejects the
NS8 registration for that domain. Module **1.0.0** is the minimum upgrade
source for this integration.

Configure the module with HTTPS redirection and a certificate trusted by its
consumers. Then enable the provider on the instance.

```bash
api-cli run module/keycloak1/configure-ns8-sso --data '{"enabled":true}'
```

The first activation restarts Keycloak briefly to create a service account.
Its credentials are stored in the module's private state and included in NS8
backups. Subsequent activations reuse those credentials.

Consuming modules declare `keycloak@any:clientadm`, bind their user domain,
and use `register-client` to obtain client credentials. A realm is created when
the first module registers for its domain. The issuer is
`https://<host>/realms/<user-domain>`. Registrations are removed when their
owning module is removed or unbound.

Disable NS8 SSO before changing the provider hostname. Disabling withdraws
the service record, deletes the managed module clients, and releases NS8
bindings for the managed domains. Keycloak retains the realms and their LDAP
federation settings.

```bash
api-cli run module/keycloak1/configure-ns8-sso --data '{"enabled":false}'
```

See the [NS8 single sign-on developer contract](https://nethserver.github.io/ns8-core/core/user_domains/#single-sign-on)
and the [NS8 application SSO tracking issue](https://github.com/NethServer/dev/issues/8258).
