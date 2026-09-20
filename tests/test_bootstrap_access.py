from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
import pytest

from knowledge_core.api.bootstrap_admission import (
    BOOTSTRAP_KEY_HEADER,
    BootstrapAdmission,
    bootstrap_principal_dependency,
)
from knowledge_core.api.bootstrap_contract import (
    BOOTSTRAP_PRINCIPAL_REF,
    DEFAULT_BIND_HOST,
    BootstrapContract,
    BootstrapOperation,
)


def _semantic_client(
    admission: BootstrapAdmission,
    operation: BootstrapOperation,
):
    app = FastAPI()
    calls: list[str] = []
    principal_dependency = bootstrap_principal_dependency(
        admission,
        operation=operation,
    )

    @app.post("/semantic")
    def semantic_operation(
        principal: str = Depends(principal_dependency),
    ):
        calls.append(principal)
        return {"principal": principal}

    return TestClient(app), calls


def test_bootstrap_contract_defaults_to_loopback_and_allows_bind_override():
    default = BootstrapContract.from_env({})
    override = BootstrapContract.from_env(
        {"KNOWLEDGE_CORE_BIND_HOST": "10.0.0.25"}
    )

    assert default.bind_host == DEFAULT_BIND_HOST == "127.0.0.1"
    assert override.bind_host == "10.0.0.25"
    assert default.principal_ref == BOOTSTRAP_PRINCIPAL_REF == "local_owner"
    assert set(default.allowed_operations) == set(BootstrapOperation)


def test_bootstrap_contract_rejects_invalid_bootstrap_identity_or_bind_host():
    with pytest.raises(ValueError, match="bind host"):
        BootstrapContract(bind_host="   ")

    with pytest.raises(ValueError, match="local_owner"):
        BootstrapContract(principal_ref="different-owner")


def test_bootstrap_admission_loads_key_without_exposing_it_in_repr():
    admission = BootstrapAdmission.from_env(
        {"KNOWLEDGE_CORE_BOOTSTRAP_KEY": "private-test-key"}
    )

    assert admission.contract.bind_host == "127.0.0.1"
    assert "private-test-key" not in repr(admission)

    with pytest.raises(RuntimeError, match="KNOWLEDGE_CORE_BOOTSTRAP_KEY"):
        BootstrapAdmission.from_env({})


def test_missing_or_invalid_key_is_rejected_before_semantic_operation():
    admission = BootstrapAdmission(
        contract=BootstrapContract(),
        api_key="correct-key",
    )
    client, calls = _semantic_client(admission, BootstrapOperation.SEARCH)
    try:
        missing = client.post("/semantic")
        invalid = client.post(
            "/semantic",
            headers={BOOTSTRAP_KEY_HEADER: "wrong-key"},
        )
    finally:
        client.close()

    assert missing.status_code == 401
    assert invalid.status_code == 401
    assert missing.json() == {"detail": "bootstrap authentication failed"}
    assert invalid.json() == {"detail": "bootstrap authentication failed"}
    assert calls == []


def test_valid_key_maps_to_fixed_local_owner_and_ignores_spoofed_caller():
    admission = BootstrapAdmission(
        contract=BootstrapContract(),
        api_key="correct-key",
    )
    client, calls = _semantic_client(admission, BootstrapOperation.STATUS)
    try:
        response = client.post(
            "/semantic",
            headers={
                BOOTSTRAP_KEY_HEADER: "correct-key",
                "X-Knowledge-Caller": "spoofed-principal",
            },
        )
    finally:
        client.close()

    assert response.status_code == 200
    assert response.json() == {"principal": "local_owner"}
    assert calls == ["local_owner"]


def test_authenticated_but_unadmitted_operation_is_rejected_before_handler():
    admission = BootstrapAdmission(
        contract=BootstrapContract(
            allowed_operations=frozenset({BootstrapOperation.STATUS})
        ),
        api_key="correct-key",
    )
    client, calls = _semantic_client(admission, BootstrapOperation.STORE)
    try:
        response = client.post(
            "/semantic",
            headers={BOOTSTRAP_KEY_HEADER: "correct-key"},
        )
    finally:
        client.close()

    assert response.status_code == 403
    assert response.json() == {"detail": "bootstrap operation is not allowed"}
    assert calls == []
