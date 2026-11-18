# register-client input Schema

```txt
http://schema.nethserver.org/keycloak/register-client-input.json
```

Create or update the calling module's OIDC client for a bound NS8 user domain. The client ID is the module ID.

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                               |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :--------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Forbidden             | none                | [register-client-input.json](keycloak/register-client-input.json "open original schema") |

## register-client input Type

`object` ([register-client input](register-client-input.md))

## register-client input Examples

```json
{
  "domain": "dp.example.org",
  "redirect_uris": [
    "https://cloud.example.org/apps/user_oidc/code"
  ],
  "post_logout_redirect_uris": [
    "https://cloud.example.org/*"
  ],
  "web_origins": [
    "https://cloud.example.org"
  ]
}
```

```json
{
  "domain": "dp.example.org",
  "redirect_uris": [
    "https://webmail.example.org/index.php/login/oauth"
  ],
  "audience": [
    "mail1"
  ],
  "rotate_secret": true
}
```

# register-client input Properties

| Property                                                | Type      | Required | Nullable       | Defined by                                                                                                                                                                                      |
| :------------------------------------------------------ | :-------- | :------- | :------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [domain](#domain)                                       | `string`  | Required | cannot be null | [register-client input](register-client-input-properties-domain.md "http://schema.nethserver.org/keycloak/register-client-input.json#/properties/domain")                                       |
| [redirect_uris](#redirect_uris)                         | `array`   | Optional | cannot be null | [register-client input](register-client-input-properties-redirect_uris.md "http://schema.nethserver.org/keycloak/register-client-input.json#/properties/redirect_uris")                         |
| [post_logout_redirect_uris](#post_logout_redirect_uris) | `array`   | Optional | cannot be null | [register-client input](register-client-input-properties-post_logout_redirect_uris.md "http://schema.nethserver.org/keycloak/register-client-input.json#/properties/post_logout_redirect_uris") |
| [web_origins](#web_origins)                             | `array`   | Optional | cannot be null | [register-client input](register-client-input-properties-web_origins.md "http://schema.nethserver.org/keycloak/register-client-input.json#/properties/web_origins")                             |
| [audience](#audience)                                   | `array`   | Optional | cannot be null | [register-client input](register-client-input-properties-audience.md "http://schema.nethserver.org/keycloak/register-client-input.json#/properties/audience")                                   |
| [rotate_secret](#rotate_secret)                         | `boolean` | Optional | cannot be null | [register-client input](register-client-input-properties-rotate_secret.md "http://schema.nethserver.org/keycloak/register-client-input.json#/properties/rotate_secret")                         |
| [module_id](#module_id)                                 | `string`  | Optional | cannot be null | [register-client input](register-client-input-properties-module_id.md "http://schema.nethserver.org/keycloak/register-client-input.json#/properties/module_id")                                 |

## domain

User domain of the realm. The calling module must be bound to it

`domain`

* is required

* Type: `string`

* cannot be null

* defined in: [register-client input](register-client-input-properties-domain.md "http://schema.nethserver.org/keycloak/register-client-input.json#/properties/domain")

### domain Type

`string`

### domain Constraints

**minimum length**: the minimum number of characters for this string is: `1`

## redirect_uris

Redirect URIs of the authorization code flow. Without redirect URIs the client can only authenticate its own requests, for example token introspection

`redirect_uris`

* is optional

* Type: `string[]`

* cannot be null

* defined in: [register-client input](register-client-input-properties-redirect_uris.md "http://schema.nethserver.org/keycloak/register-client-input.json#/properties/redirect_uris")

### redirect_uris Type

`string[]`

### redirect_uris Constraints

**unique items**: all items in this array must be unique. Duplicates are not allowed.

### redirect_uris Default Value

The default value is:

```json
[]
```

## post_logout_redirect_uris

URIs where the logout redirects the user. Applications should pass their exact logout URI. If the attribute is missing, a wildcard URI for each origin of the redirect URIs is set, like <https://cloud.example.org/>\*; an empty list allows none

`post_logout_redirect_uris`

* is optional

* Type: `string[]`

* cannot be null

* defined in: [register-client input](register-client-input-properties-post_logout_redirect_uris.md "http://schema.nethserver.org/keycloak/register-client-input.json#/properties/post_logout_redirect_uris")

### post_logout_redirect_uris Type

`string[]`

### post_logout_redirect_uris Constraints

**unique items**: all items in this array must be unique. Duplicates are not allowed.

## web_origins

Allowed CORS origins

`web_origins`

* is optional

* Type: `string[]`

* cannot be null

* defined in: [register-client input](register-client-input-properties-web_origins.md "http://schema.nethserver.org/keycloak/register-client-input.json#/properties/web_origins")

### web_origins Type

`string[]`

### web_origins Constraints

**unique items**: all items in this array must be unique. Duplicates are not allowed.

### web_origins Default Value

The default value is:

```json
[]
```

## audience

Client IDs added to the audience of the tokens, for example the mail module whose Dovecot introspects them

`audience`

* is optional

* Type: `string[]`

* cannot be null

* defined in: [register-client input](register-client-input-properties-audience.md "http://schema.nethserver.org/keycloak/register-client-input.json#/properties/audience")

### audience Type

`string[]`

### audience Constraints

**unique items**: all items in this array must be unique. Duplicates are not allowed.

### audience Default Value

The default value is:

```json
[]
```

## rotate_secret

Generate a new client secret. Otherwise the current secret is returned

`rotate_secret`

* is optional

* Type: `boolean`

* cannot be null

* defined in: [register-client input](register-client-input-properties-rotate_secret.md "http://schema.nethserver.org/keycloak/register-client-input.json#/properties/rotate_secret")

### rotate_secret Type

`boolean`

### rotate_secret Default Value

The default value is:

```json
false
```

## module_id

Module that owns the client. Allowed only for tasks without a calling user, for example created by the cluster agent: otherwise the owner is the calling module

`module_id`

* is optional

* Type: `string`

* cannot be null

* defined in: [register-client input](register-client-input-properties-module_id.md "http://schema.nethserver.org/keycloak/register-client-input.json#/properties/module_id")

### module_id Type

`string`

### module_id Constraints

**pattern**: the string must match the following regular expression:&#x20;

```regexp
^[a-zA-Z0-9_.-]+$
```

[try pattern](https://regexr.com/?expression=%5E%5Ba-zA-Z0-9_.-%5D%2B%24 "try regular expression with regexr.com")
