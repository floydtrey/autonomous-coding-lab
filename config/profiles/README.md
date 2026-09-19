# Controller Profiles

Role profiles live here as external configuration. Controller source code must not
hardcode model names, harnesses, endpoints, context sizes, temperatures, prompts,
or role-specific runtime choices.

The first role-profile skeleton is `determiner-general.json`. It is intentionally
unbound to a concrete runtime adapter until the Determiner integration pass.

A profile will use the `acl-controller-profile:v1` schema and identify at least:

- `profile_id`
- `role`
- `adapter_id`
- opaque `settings`
- opaque `instructions`
- optional `tool_profile`
- optional metadata

`config/routing.json` maps an exact role/work-type/complexity selection to one
profile ID. Missing mappings fail explicitly; Controller does not silently fall
back to another profile.

A route may use `"work_type": null` for a role that must run before classification
exists. Determiner uses this role-global route. Post-classification roles should
continue to use explicit work-type routes.
