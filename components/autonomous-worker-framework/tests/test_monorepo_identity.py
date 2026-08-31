import json
from dataclasses import replace
from pathlib import Path

import pytest

from tools.monorepo_identity import (
    FRAMEWORK_PREFIX,
    POLICY_ID,
    POLICY_PATH,
    SCHEMA_VERSION,
    IdentityPolicyError,
    SourceProvenance,
    canonical_policy_json,
    identity_policy_digest,
    parse_identity_policy,
    require_source_provenance,
)


ROOT = Path(__file__).resolve().parents[3]
POLICY_FILE = ROOT / POLICY_PATH


def policy_mapping():
    return json.loads(POLICY_FILE.read_text(encoding="utf-8"))


def render(value):
    return canonical_policy_json(value)


def test_tracked_policy_is_canonical_framework_only_and_separates_identities():
    raw = POLICY_FILE.read_bytes()
    policy = parse_identity_policy(raw)

    assert raw == render(policy_mapping()).encode("utf-8")
    assert policy.schema_version == SCHEMA_VERSION
    assert policy.policy_id == POLICY_ID
    assert policy.activation_state == "FRAMEWORK_ONLY"
    assert policy.execution_authority == "DISABLED"
    assert policy.deferred_participants == ("worker-lab",)
    assert policy.integration_policy.canonical_component_prefix == FRAMEWORK_PREFIX
    assert policy.integration_policy.shared_dependency_paths == (POLICY_PATH,)
    assert "monorepo_commit" not in raw.decode("utf-8")
    assert identity_policy_digest(raw).startswith("sha256:")


@pytest.mark.parametrize(
    "mutation",
    (
        lambda value: value.update({"unknown": True}),
        lambda value: value.pop("execution_authority"),
        lambda value: value.update({"execution_authority": "ENABLED"}),
        lambda value: value.update({"activation_state": "ACTIVE"}),
        lambda value: value.update({"deferred_participants": []}),
    ),
)
def test_policy_rejects_unknown_missing_or_authority_expanding_fields(mutation):
    value = policy_mapping()
    mutation(value)

    with pytest.raises(IdentityPolicyError):
        parse_identity_policy(render(value))


def test_policy_rejects_noncanonical_json_and_duplicate_fields():
    value = policy_mapping()
    with pytest.raises(IdentityPolicyError, match="canonical JSON"):
        parse_identity_policy(json.dumps(value))

    duplicate = render(value).replace(
        '  "policy_id":',
        '  "policy_id": "duplicate",\n  "policy_id":',
        1,
    )
    with pytest.raises(IdentityPolicyError, match="duplicate"):
        parse_identity_policy(duplicate)


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("canonical_component_prefix", "components/autonomous-worker-framework-evil"),
        ("canonical_component_prefix", "../autonomous-worker-framework"),
        ("source_adapter_path", "tools/other.py"),
        ("adapter_integration_path", "tools/worker_lab_adapter.py"),
        ("component_scope", "selected-files:v1"),
        ("shared_dependency_paths", ["config/other.json"]),
    ),
)
def test_policy_rejects_prefix_path_or_dependency_closure_substitution(
    field, replacement
):
    value = policy_mapping()
    value["integration_policy"][field] = replacement

    with pytest.raises(IdentityPolicyError):
        parse_identity_policy(render(value))


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("commit", "A" * 40),
        ("tree", "1" * 39),
        ("adapter_blob", "g" * 40),
        ("adapter_sha256", "1" * 63),
        ("recovery_bundle_sha256", "z" * 64),
    ),
)
def test_policy_rejects_noncanonical_source_identities(field, replacement):
    value = policy_mapping()
    value["framework"][field] = replacement

    with pytest.raises(IdentityPolicyError):
        parse_identity_policy(render(value))


def test_expected_source_provenance_rejects_stale_or_substituted_source():
    policy = parse_identity_policy(POLICY_FILE.read_bytes())
    require_source_provenance(policy, policy.framework)

    stale = replace(policy.framework, commit="0" * 40)
    with pytest.raises(IdentityPolicyError, match="stale or substituted"):
        require_source_provenance(policy, stale)


def test_policy_rejects_duplicate_or_unsorted_shared_dependency_paths():
    for paths in (
        [POLICY_PATH, POLICY_PATH],
        ["z.json", POLICY_PATH],
    ):
        value = policy_mapping()
        value["integration_policy"]["shared_dependency_paths"] = paths
        with pytest.raises(IdentityPolicyError):
            parse_identity_policy(render(value))


def test_source_provenance_type_remains_explicit():
    policy = parse_identity_policy(POLICY_FILE.read_bytes())
    assert isinstance(policy.framework, SourceProvenance)
