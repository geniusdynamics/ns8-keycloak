# Untitled array in register-client input Schema

```txt
http://schema.nethserver.org/keycloak/register-client-input.json#/properties/web_origins
```

Allowed CORS origins

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                 |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :----------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [register-client-input.json\*](keycloak/register-client-input.json "open original schema") |

## web_origins Type

`string[]`

## web_origins Constraints

**unique items**: all items in this array must be unique. Duplicates are not allowed.

## web_origins Default Value

The default value is:

```json
[]
```
