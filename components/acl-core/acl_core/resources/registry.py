"""In-memory registry of generic target/resource references."""
from __future__ import annotations

from ..diagnostics import span
from ..errors import CoreError
from .models import ResourceRef, TargetRef


class ResourceRegistry:
    component = "core.resources"

    def __init__(self) -> None:
        self._resources: dict[str, ResourceRef] = {}
        self._targets: dict[str, TargetRef] = {}

    def register_resource(self, resource: ResourceRef) -> ResourceRef:
        with span(self.component, "register_resource", resource_id=resource.resource_id):
            existing = self._resources.get(resource.resource_id)
            if existing is not None and existing.digest() != resource.digest():
                raise CoreError(
                    "RESOURCE_CONFLICT",
                    "resource identity is already bound to different content",
                    {"resource_id": resource.resource_id},
                )
            self._resources[resource.resource_id] = resource
            return resource

    def register_target(self, target: TargetRef) -> TargetRef:
        with span(self.component, "register_target", target_id=target.target_id):
            for resource in target.resources:
                self.register_resource(resource)
            existing = self._targets.get(target.target_id)
            if existing is not None and existing.digest() != target.digest():
                raise CoreError(
                    "TARGET_CONFLICT",
                    "target identity is already bound to different content",
                    {"target_id": target.target_id},
                )
            self._targets[target.target_id] = target
            return target

    def resource(self, resource_id: str) -> ResourceRef:
        with span(self.component, "resource", resource_id=resource_id):
            try:
                return self._resources[resource_id]
            except KeyError as exc:
                raise CoreError("RESOURCE_MISSING", "resource is not registered", {"resource_id": resource_id}) from exc

    def target(self, target_id: str) -> TargetRef:
        with span(self.component, "target", target_id=target_id):
            try:
                return self._targets[target_id]
            except KeyError as exc:
                raise CoreError("TARGET_MISSING", "target is not registered", {"target_id": target_id}) from exc

    def resources(self) -> tuple[ResourceRef, ...]:
        return tuple(self._resources[key] for key in sorted(self._resources))

    def targets(self) -> tuple[TargetRef, ...]:
        return tuple(self._targets[key] for key in sorted(self._targets))
