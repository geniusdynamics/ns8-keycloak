# ns8-keycloak

A [NethServer 8](https://github.com/NethServer/ns8-core) module for
[Keycloak](https://www.keycloak.org/), the open source identity and access
management server: single sign-on, OpenID Connect, OAuth 2.0 and SAML.

The module runs a pod with two rootless Podman containers:

- `keycloak-app`: Keycloak, in production mode (`start`), serving plain HTTP
  on container port 8080 behind Traefik.
- `postgresql-app`: PostgreSQL, the only storage used by Keycloak.

## Install

Instantiate the module with:

```bash
add-module ghcr.io/geniusdynamics/keycloak:latest 1
```

The output will return the instance name:

```json
{
  "module_id": "keycloak1",
  "image_name": "keycloak",
  "image_url": "ghcr.io/geniusdynamics/keycloak:latest"
}
```

## Configure

Let's assume that the keycloak instance is named `keycloak1`.

Launch `configure-module`, by setting the following parameters:

- `host`: a fully qualified domain name for the application
- `http2https`: enable or disable HTTP to HTTPS redirection (true/false)
- `lets_encrypt`: enable or disable Let's Encrypt certificate (true/false)

Example:

```bash
api-cli run configure-module --agent module/keycloak1 --data - <<EOF
{
  "host": "keycloak.example.org",
  "http2https": true,
  "lets_encrypt": false
}
