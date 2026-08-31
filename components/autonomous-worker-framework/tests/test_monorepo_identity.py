import hashlib
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
    integration_identity_digest,
    parse_identity_policy,
    require_source_provenance,
    verify_framework_integration,
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


def integration_fixture(tmp_path, monkeypatch):
    root = tmp_path / "acl"
    component = root / FRAMEWORK_PREFIX
    adapter_path = component / "tools" / "worker_lab_adapter.py"
    policy_path = root / POLICY_PATH
    adapter_path.parent.mkdir(parents=True)
    policy_path.parent.mkdir(parents=True)

    source_adapter = b"source adapter\n"
    current_adapter = b"integrated adapter\n"
    adapter_path.write_bytes(current_adapter)
    value = policy_mapping()
    identities = {
        "source_commit": "1" * 40,
        "source_tree": "2" * 40,
        "source_adapter_blob": "3" * 40,
        "import_commit": "4" * 40,
        "head": "5" * 40,
        "monorepo_tree": "6" * 40,
        "component_tree": "7" * 40,
        "adapter_blob": "8" * 40,
        "policy_blob": "9" * 40,
    }
    value["framework"]["commit"] = identities["source_commit"]
    value["framework"]["tree"] = identities["source_tree"]
    value["framework"]["adapter_blob"] = identities["source_adapter_blob"]
    value["framework"]["adapter_sha256"] = hashlib.sha256(source_adapter).hexdigest()
    value["integration_policy"]["import_commit"] = identities["import_commit"]
    policy_bytes = render(value).encode("utf-8")
    policy_path.write_bytes(policy_bytes)
    policy = parse_identity_policy(policy_bytes)

    responses = {
        ("rev-parse", "--show-toplevel"): f"{root}\n".encode(),
        ("rev-parse", "HEAD"): f"{identities['head']}\n".encode(),
        ("rev-parse", "HEAD^{tree}"): f"{identities['monorepo_tree']}\n".encode(),
        (
            "rev-parse",
            f"{identities['source_commit']}^{{tree}}",
        ): f"{identities['source_tree']}\n".encode(),
        (
            "rev-parse",
            f"{identities['source_commit']}:tools/worker_lab_adapter.py",
        ): f"{identities['source_adapter_blob']}\n".encode(),
        (
            "show",
            f"{identities['source_commit']}:tools/worker_lab_adapter.py",
        ): source_adapter,
        (
            "rev-parse",
            f"{identities['import_commit']}:{FRAMEWORK_PREFIX}",
        ): f"{identities['source_tree']}\n".encode(),
        (
            "rev-parse",
            f"{identities['import_commit']}:{FRAMEWORK_PREFIX}/tools/worker_lab_adapter.py",
        ): f"{identities['source_adapter_blob']}\n".encode(),
        (
            "rev-parse",
            f"HEAD:{FRAMEWORK_PREFIX}",
        ): f"{identities['component_tree']}\n".encode(),
        (
            "rev-parse",
            f"HEAD:{FRAMEWORK_PREFIX}/tools/worker_lab_adapter.py",
        ): f"{identities['adapter_blob']}\n".encode(),
        (
            "show",
            f"HEAD:{FRAMEWORK_PREFIX}/tools/worker_lab_adapter.py",
        ): current_adapter,
        ("rev-parse", f"HEAD:{POLICY_PATH}"): f"{identities['policy_blob']}\n".encode(),
        ("show", f"HEAD:{POLICY_PATH}"): policy_bytes,
        (
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            "--",
            FRAMEWORK_PREFIX,
            POLICY_PATH,
        ): b"",
    }

    def run_git(repository_root, args):
        assert repository_root == root
        try:
            return responses[args]
        except KeyError as exc:
            raise AssertionError(args) from exc

    return root, component, policy, identities, responses, run_git


def test_framework_integration_verifies_separate_provenance_and_current_identity(
    tmp_path, monkeypatch
):
    _, component, policy, identities, _, run_git = integration_fixture(
        tmp_path, monkeypatch
    )

    identity = verify_framework_integration(
        policy,
        expected_monorepo_commit=identities["head"],
        component_root=component,
        git_runner=run_git,
    )

    assert identity.source_commit == identities["source_commit"]
    assert identity.monorepo_commit == identities["head"]
    assert identity.source_tree == identities["source_tree"]
    assert identity.component_tree == identities["component_tree"]
    assert identity.adapter_blob == identities["adapter_blob"]
    assert integration_identity_digest(identity).startswith("sha256:")


@pytest.mark.parametrize(
    ("response_key", "replacement", "message"),
    (
        (("rev-parse", "HEAD"), b"0" * 40 + b"\n", "monorepo commit"),
        (
            ("rev-parse", "1" * 40 + "^{tree}"),
            b"0" * 40 + b"\n",
            "source tree",
        ),
        (
            ("show", "1" * 40 + ":tools/worker_lab_adapter.py"),
            b"substituted source adapter\n",
            "source adapter digest",
        ),
        (
            ("rev-parse", "4" * 40 + f":{FRAMEWORK_PREFIX}"),
            b"0" * 40 + b"\n",
            "import subtree",
        ),
        (
            (
                "rev-parse",
                "4" * 40 + f":{FRAMEWORK_PREFIX}/tools/worker_lab_adapter.py",
            ),
            b"0" * 40 + b"\n",
            "imported adapter",
        ),
        (
            (
                "status",
                "--porcelain=v1",
                "-z",
                "--untracked-files=all",
                "--",
                FRAMEWORK_PREFIX,
                POLICY_PATH,
            ),
            b"?? components/autonomous-worker-framework/evil.py\x00",
            "dependency set is dirty",
        ),
    ),
)
def test_framework_integration_fails_on_stale_dirty_or_substituted_git_evidence(
    tmp_path, monkeypatch, response_key, replacement, message
):
    _, component, policy, identities, responses, run_git = integration_fixture(
        tmp_path, monkeypatch
    )
    responses[response_key] = replacement

    with pytest.raises(IdentityPolicyError, match=message):
        verify_framework_integration(
            policy,
            expected_monorepo_commit=identities["head"],
            component_root=component,
            git_runner=run_git,
        )


def test_framework_integration_rejects_worktree_adapter_or_policy_substitution(
    tmp_path, monkeypatch
):
    root, component, policy, identities, _, run_git = integration_fixture(
        tmp_path, monkeypatch
    )
    (component / "tools" / "worker_lab_adapter.py").write_bytes(b"substituted\n")
    with pytest.raises(IdentityPolicyError, match="adapter worktree"):
        verify_framework_integration(
            policy,
            expected_monorepo_commit=identities["head"],
            component_root=component,
            git_runner=run_git,
        )

    _, component, policy, identities, _, run_git = integration_fixture(
        tmp_path / "second", monkeypatch
    )
    root = component.parents[1]
    (root / POLICY_PATH).write_bytes(b"{}\n")
    with pytest.raises(IdentityPolicyError, match="policy worktree"):
        verify_framework_integration(
            policy,
            expected_monorepo_commit=identities["head"],
            component_root=component,
            git_runner=run_git,
        )


def test_framework_integration_rejects_component_root_or_reparse_substitution(
    tmp_path, monkeypatch
):
    root, component, policy, identities, _, run_git = integration_fixture(
        tmp_path, monkeypatch
    )
    lookalike = root / "components" / "autonomous-worker-framework-evil"
    lookalike.mkdir()
    with pytest.raises(IdentityPolicyError, match="component root is substituted"):
        verify_framework_integration(
            policy,
            expected_monorepo_commit=identities["head"],
            component_root=lookalike,
            git_runner=run_git,
        )

    adapter_path = component / "tools" / "worker_lab_adapter.py"
    from tools import monorepo_identity

    original = monorepo_identity._is_link_or_junction
    monkeypatch.setattr(
        monorepo_identity,
        "_is_link_or_junction",
        lambda path: path == adapter_path or original(path),
    )
    with pytest.raises(IdentityPolicyError, match="linked or reparse"):
        verify_framework_integration(
            policy,
            expected_monorepo_commit=identities["head"],
            component_root=component,
            git_runner=run_git,
        )


def test_framework_integration_rejects_git_root_substitution(tmp_path, monkeypatch):
    root, component, policy, identities, responses, run_git = integration_fixture(
        tmp_path, monkeypatch
    )
    other_root = root / "other"
    other_root.mkdir()
    responses[("rev-parse", "--show-toplevel")] = f"{other_root}\n".encode()

    with pytest.raises(IdentityPolicyError, match="substituted monorepo root"):
        verify_framework_integration(
            policy,
            expected_monorepo_commit=identities["head"],
            component_root=component,
            git_runner=run_git,
        )


def test_framework_integration_uses_only_declared_cleanliness_closure(
    tmp_path, monkeypatch
):
    _, component, policy, identities, responses, run_git = integration_fixture(
        tmp_path, monkeypatch
    )

    verify_framework_integration(
        policy,
        expected_monorepo_commit=identities["head"],
        component_root=component,
        git_runner=run_git,
    )

    status_calls = [args for args in responses if args and args[0] == "status"]
    assert status_calls == [
        (
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            "--",
            FRAMEWORK_PREFIX,
            POLICY_PATH,
        )
    ]
