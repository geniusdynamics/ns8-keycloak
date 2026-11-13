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

Requires NS8 core `3.12.4-0` or newer.

## Network and access

- Reserves 1 TCP port(s) on the node. The web application is published through Traefik on the configured host name.
- Runs rootless.
- Declares these NS8 authorizations: `traefik@node:routeadm`.

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
