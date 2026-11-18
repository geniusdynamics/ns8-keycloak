# Untitled array in register-client input Schema

```txt
http://schema.nethserver.org/keycloak/register-client-input.json#/properties/audience
```

Client IDs added to the audience of the tokens, for example the mail module whose Dovecot introspects them

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                 |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :----------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [register-client-input.json\*](keycloak/register-client-input.json "open original schema") |

## audience Type

`string[]`

## audience Constraints

**unique items**: all items in this array must be unique. Duplicates are not allowed.

## audience Default Value

The default value is:

```json
[]
```
