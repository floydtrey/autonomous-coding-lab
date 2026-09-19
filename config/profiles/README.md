# Controller Profiles

Role profiles live here as external configuration. Controller source code must not
hardcode model names, harnesses, endpoints, context sizes, temperatures, prompts,
or role-specific runtime choices.

No production profiles exist yet because AI roles have not been built.

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
