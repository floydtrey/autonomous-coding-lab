"""The single Pi configuration's readiness-to-binding bridge, not activation."""
from __future__ import annotations

from pathlib import Path

from .canonical import canonical_digest
from .errors import LabValidationError
from .pi_worker import PI_ADAPTER_ID, load_pi_worker, resolve_pi_worker
from .provider_binding import ProviderBinding, PROVIDER_BINDING_SCHEMA
from .runtime_settings import RuntimeSettingsProfile

CONFIG_PATH = Path(__file__).resolve().parents[3] / 'config/pi-local-worker.json'
PI_CANDIDATE_ID = 'pi-local-files'


def require(ok: bool, detail: str) -> None:
    if not ok:
        raise LabValidationError('PI_BINDING_INVALID', detail)


def check_runtime_readiness(worker: dict, *, expected_digest: str,
                            version: dict, tags: dict, processes: dict) -> dict:
    """Consume trusted /api/version, /api/tags and /api/ps observations.

    No model call or context benchmark. Server context is distinct from Pi metadata.
    The legacy binding's host_provider_qualification_digest holds this readiness
    evidence for Pi; it does not assert the deferred full S16 qualification.
    """
    worker = resolve_pi_worker(worker, expected_digest=expected_digest)
    require(isinstance(version, dict) and version.get('version') == worker['provider_version'], 'provider version differs')
    require(isinstance(tags, dict) and isinstance(tags.get('models'), list), 'invalid model observation')
    found = [m for m in tags['models'] if isinstance(m, dict) and m.get('name') == worker['model_name']]
    require(len(found) == 1, 'exact configured model must exist once')
    model = found[0]
    require(model.get('digest') == worker['model_digest'].removeprefix('sha256:')
            and model.get('details', {}).get('quantization_level') == worker['quantization'], 'model identity differs')
    require(isinstance(processes, dict) and isinstance(processes.get('models'), list), 'invalid running model observation')
    loaded = [m for m in processes['models'] if isinstance(m, dict) and m.get('name') == worker['model_name']]
    require(len(loaded) == 1 and loaded[0].get('digest') == model['digest'], 'configured model must already be loaded')
    context = loaded[0].get('context_length')
    require(type(context) is int and context >= worker['required_effective_context_tokens'], 'prestarted server context is inadequate or unknown')
    return {
        'schema_version': 'acl-pi-readiness:v1', 'configuration_digest': expected_digest,
        'endpoint': worker['endpoint'], 'provider_version': version['version'],
        'model_name': model['name'], 'model_digest': worker['model_digest'],
        'model_metadata_digest': canonical_digest(model), 'server_context_tokens': context,
    }


def create_pi_provider_binding(binding_id: str, *, worker: dict, expected_digest: str,
                               version: dict, tags: dict, processes: dict) -> ProviderBinding:
    worker = resolve_pi_worker(worker, expected_digest=expected_digest)
    evidence = check_runtime_readiness(worker, expected_digest=expected_digest, version=version, tags=tags, processes=processes)
    binding = ProviderBinding(
        PROVIDER_BINDING_SCHEMA, binding_id, 1,
        worker['runtime_requirement']['profile_id'], worker['runtime_requirement_digest'],
        canonical_digest(evidence), PI_CANDIDATE_ID, 1, expected_digest,
        PI_ADAPTER_ID, worker['tool_surface_id'], worker['provider_kind'],
        worker['model_name'], worker['model_digest'], evidence['model_metadata_digest'],
        worker['runtime_settings']['profile_id'], worker['runtime_settings_digest'],
    )
    return ProviderBinding.from_mapping(binding.to_dict())


def validate_pi_binding(binding: ProviderBinding, settings: RuntimeSettingsProfile | None = None) -> dict:
    worker = load_pi_worker(CONFIG_PATH, expected_digest=binding.qualification_candidate_digest)
    require(binding.binding_version == 1 and binding.qualification_candidate_version == 1
            and binding.qualification_candidate_id == PI_CANDIDATE_ID, 'Pi candidate identity differs')
    for name in ('provider_adapter_id', 'tool_surface_id', 'provider_kind', 'model_name',
                 'model_digest', 'runtime_requirement_digest', 'runtime_settings_digest'):
        require(getattr(binding, name) == worker[name], f'Pi binding {name} differs')
    require(binding.runtime_requirement_profile_id == worker['runtime_requirement']['profile_id']
            and binding.runtime_settings_profile_id == worker['runtime_settings']['profile_id'], 'Pi runtime profile differs')
    if settings is not None:
        require(settings.to_dict() == worker['runtime_settings'], 'Pi settings differ')
    return worker
