"""Translate an accepted Planner Pass into a bounded Worker authority grant.

The authority mechanism itself remains shared Core/Controller infrastructure.
This module only maps Planner's Pass filesystem intent into that generic grant
contract.
"""
from __future__ import annotations

from dataclasses import dataclass

from acl_core import AuthorityEnvelope, AuthorityRequest, FilesystemOperation, ToolRegistry
from acl_core.diagnostics import emit
from acl_roles.planner import PassSpec

from ..configuration import ProfileResolver, ProfileSelector
from ..errors import ControllerError
from ..state import WorkflowStateService
from ..tools import (
    FS_CREATE_TEXT,
    FS_DELETE_PATH,
    FS_LIST_DIRECTORY,
    FS_MOVE_PATH,
    FS_READ_TEXT,
    FS_WRITE_TEXT,
    ToolProfileResolver,
    filesystem_scope,
)
from .enforcement import AuthorityCoordinator
from .filesystem import FilesystemAuthorityCoordinator


@dataclass(frozen=True)
class PassAuthorityBinding:
    grant_id: str
    tool_ids: tuple[str, ...]
    capabilities: tuple[str, ...]
    resource_scopes: tuple[str, ...]


class PassAuthorityService:
    """Create the least Worker grant implied by one accepted Pass."""

    component = "controller.pass_authority"

    def __init__(
        self,
        *,
        state: WorkflowStateService,
        authority: AuthorityCoordinator,
        filesystem_authority: FilesystemAuthorityCoordinator,
        profiles: ProfileResolver,
        tool_profiles: ToolProfileResolver,
        tools: ToolRegistry,
    ) -> None:
        self.state = state
        self.authority = authority
        self.filesystem_authority = filesystem_authority
        self.profiles = profiles
        self.tool_profiles = tool_profiles
        self.tools = tools

    def bind_worker_pass(
        self,
        workflow_id: str,
        *,
        work_type_id: str | None,
        complexity: str | None,
        pass_spec: PassSpec,
    ) -> PassAuthorityBinding:
        if not isinstance(pass_spec, PassSpec):
            raise ControllerError(
                "CONTROLLER_PASS_AUTHORITY_INVALID",
                "pass authority requires PassSpec",
            )

        profile = self.profiles.resolve(
            ProfileSelector(
                role="worker",
                work_type=work_type_id,
                complexity=complexity,
            )
        )
        configured_tools = self.tool_profiles.resolve(profile.tool_profile)
        needed_tools, resource_scopes = self._requirements(pass_spec)

        missing = tuple(sorted(set(needed_tools) - set(configured_tools)))
        if missing:
            raise ControllerError(
                "CONTROLLER_PASS_TOOL_PROFILE_DENIED",
                "Pass requires tools outside the configured Worker tool profile",
                {
                    "pass_id": pass_spec.pass_id,
                    "tool_profile": profile.tool_profile,
                    "missing_tool_ids": list(missing),
                },
            )

        ceiling_capabilities = self._capabilities(configured_tools)
        required_capabilities = self._capabilities(needed_tools)

        request = AuthorityRequest(
            capabilities=required_capabilities,
            resource_scopes=resource_scopes,
            tool_scopes=needed_tools,
            reason=f"accepted Planner Pass {pass_spec.pass_id}",
        )
        ceiling = AuthorityEnvelope(
            capabilities=ceiling_capabilities,
            resource_scopes=resource_scopes,
            tool_scopes=configured_tools,
        )

        workflow = self.state.read(workflow_id)
        subject = f"worker:{pass_spec.pass_id}"
        if workflow.authority_grant_id is not None:
            try:
                current = self.authority.grant(workflow.authority_grant_id)
            except ControllerError:
                current = None
            if (
                current is not None
                and current.subject == subject
                and current.authority == request.envelope()
            ):
                return PassAuthorityBinding(
                    grant_id=current.grant_id,
                    tool_ids=current.authority.tool_scopes,
                    capabilities=current.authority.capabilities,
                    resource_scopes=current.authority.resource_scopes,
                )

        grant = self.authority.issue(
            ceiling=ceiling,
            request=request,
            issuer="controller.pass_authority",
            subject=subject,
        )
        self.state.transition(
            workflow_id,
            workflow.status,
            authority_grant_id=grant.grant_id,
        )
        emit(
            "INFO",
            self.component,
            "bind_worker_pass",
            "worker_pass_authority_bound",
            workflow_id=workflow_id,
            pass_id=pass_spec.pass_id,
            grant_id=grant.grant_id,
            profile_id=profile.profile_id,
            tool_profile=profile.tool_profile,
            tool_ids=list(grant.authority.tool_scopes),
            capabilities=list(grant.authority.capabilities),
            resource_scope_count=len(grant.authority.resource_scopes),
        )
        return PassAuthorityBinding(
            grant_id=grant.grant_id,
            tool_ids=grant.authority.tool_scopes,
            capabilities=grant.authority.capabilities,
            resource_scopes=grant.authority.resource_scopes,
        )

    def _requirements(self, pass_spec: PassSpec) -> tuple[tuple[str, ...], tuple[str, ...]]:
        tool_ids: set[str] = set()
        resource_scopes: set[str] = set()

        for task in pass_spec.tasks:
            filesystem = task.filesystem
            for path in filesystem.read_paths:
                decision = self.filesystem_authority.require_allowed(
                    FilesystemOperation.READ,
                    path,
                )
                tool_ids.update((FS_READ_TEXT, FS_LIST_DIRECTORY))
                resource_scopes.add(
                    filesystem_scope(FilesystemOperation.READ, decision.path)
                )

            for path in filesystem.write_paths:
                decision = self.filesystem_authority.require_allowed(
                    FilesystemOperation.WRITE,
                    path,
                )
                tool_ids.add(FS_WRITE_TEXT)
                resource_scopes.add(
                    filesystem_scope(FilesystemOperation.WRITE, decision.path)
                )

            for path in filesystem.create_paths:
                decision = self.filesystem_authority.require_allowed(
                    FilesystemOperation.CREATE,
                    path,
                )
                tool_ids.add(FS_CREATE_TEXT)
                resource_scopes.add(
                    filesystem_scope(FilesystemOperation.CREATE, decision.path)
                )

            for path in filesystem.delete_paths:
                decision = self.filesystem_authority.require_allowed(
                    FilesystemOperation.DELETE,
                    path,
                )
                tool_ids.add(FS_DELETE_PATH)
                resource_scopes.add(
                    filesystem_scope(FilesystemOperation.DELETE, decision.path)
                )

            for move in filesystem.move_paths:
                decision = self.filesystem_authority.require_allowed(
                    FilesystemOperation.MOVE,
                    move.source,
                    destination=move.destination,
                )
                if decision.destination is None:
                    raise ControllerError(
                        "CONTROLLER_PASS_AUTHORITY_INVALID",
                        "move destination did not resolve",
                        {"pass_id": pass_spec.pass_id},
                    )
                tool_ids.add(FS_MOVE_PATH)
                resource_scopes.add(
                    filesystem_scope(FilesystemOperation.MOVE, decision.path)
                )
                resource_scopes.add(
                    filesystem_scope(
                        FilesystemOperation.MOVE,
                        decision.destination,
                    )
                )

        return tuple(sorted(tool_ids)), tuple(sorted(resource_scopes))

    def _capabilities(self, tool_ids: tuple[str, ...]) -> tuple[str, ...]:
        values: set[str] = set()
        for tool_id in tool_ids:
            definition = self.tools.definition(tool_id)
            values.update(definition.required_capabilities)
        return tuple(sorted(values))
