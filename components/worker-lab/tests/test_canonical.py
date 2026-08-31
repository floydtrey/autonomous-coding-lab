import pytest

from worker_lab.canonical import canonical_digest, canonical_json
from worker_lab.errors import LabValidationError


def test_canonical_json_is_stable_and_utf8_preserving():
    first = {"z": [2, 1], "a": "café", "flag": True}
    second = {"flag": True, "a": "café", "z": [2, 1]}
    assert canonical_json(first) == '{"a":"café","flag":true,"z":[2,1]}'
    assert canonical_json(first) == canonical_json(second)
    assert canonical_digest(first) == canonical_digest(second)


@pytest.mark.parametrize("value", [1.0, float("nan"), {"nested": 2.5}])
def test_floats_fail_closed(value):
    with pytest.raises(LabValidationError) as error:
        canonical_json(value)
    assert error.value.code == "CANONICAL_FLOAT_FORBIDDEN"


def test_non_text_object_key_fails_closed():
    with pytest.raises(LabValidationError) as error:
        canonical_json({1: "bad"})
    assert error.value.code == "CANONICAL_KEY_INVALID"


def test_unsupported_value_fails_closed():
    with pytest.raises(LabValidationError) as error:
        canonical_json({"value": object()})
    assert error.value.code == "CANONICAL_VALUE_INVALID"
