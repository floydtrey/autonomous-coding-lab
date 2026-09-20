"""Filesystem authority checks for Planner PL04."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from acl_controller.authority import FilesystemAuthorityCoordinator
from acl_controller.errors import ControllerError
from acl_core import FilesystemAuthorityService, FilesystemOperation
from acl_core.errors import CoreError


class FilesystemAuthorityCoreTests(unittest.TestCase):
    def _windows_service(self) -> FilesystemAuthorityService:
        return FilesystemAuthorityService.for_acl(
            project_root="C:/Projects/ACL_Next",
            state_root="C:/Projects/ACL_Next/.acl-state",
            authority_config_path="C:/Projects/ACL_Next/config/filesystem_authority.json",
            permanent_acl_paths=(
                (
                    "C:/Projects/ACL_Next/acl_core",
                    "ACL Core is permanently protected from Worker mutation",
                ),
                (
                    "C:/Projects/ACL_Next/acl_controller",
                    "ACL Controller is permanently protected from Worker mutation",
                ),
            ),
            user_protected_paths=(
                ("C:/Frozen", "operator-frozen project"),
                ("D:/KnownGood/app.exe", "operator-frozen file"),
            ),
            system_roots=("C:/Windows", "C:/Program Files", "C:/ProgramData"),
        )

    def test_normal_project_or_user_path_is_not_semantically_blocked(self) -> None:
        service = self._windows_service()
        decision = service.evaluate(
            FilesystemOperation.WRITE,
            "C:/jackinbox/audio/recorder.html",
        )
        self.assertTrue(decision.allowed)

    def test_windows_system_path_is_hard_denied_for_mutation(self) -> None:
        service = self._windows_service()
        decision = service.evaluate(
            FilesystemOperation.WRITE,
            "C:/Windows/explorer.exe",
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.code, "FILESYSTEM_MUTATION_DENIED")
        self.assertEqual(
            str(decision.matched_protection.layer),
            "PERMANENT_SYSTEM",
        )

    def test_windows_protection_is_case_insensitive(self) -> None:
        service = self._windows_service()
        decision = service.evaluate(
            FilesystemOperation.DELETE,
            "c:/WINDOWS/System32/notepad.exe",
        )
        self.assertFalse(decision.allowed)

    def test_acl_core_and_controller_are_permanently_mutation_protected(self) -> None:
        service = self._windows_service()
        for path in (
            "C:/Projects/ACL_Next/acl_core/authority/service.py",
            "C:/Projects/ACL_Next/acl_controller/service.py",
        ):
            with self.subTest(path=path):
                self.assertFalse(
                    service.evaluate(FilesystemOperation.WRITE, path).allowed
                )

    def test_acl_state_and_authority_policy_are_permanently_protected(self) -> None:
        service = self._windows_service()
        self.assertFalse(
            service.evaluate(
                FilesystemOperation.DELETE,
                "C:/Projects/ACL_Next/.acl-state/workflows/workflow_x.json",
            ).allowed
        )
        self.assertFalse(
            service.evaluate(
                FilesystemOperation.WRITE,
                "C:/Projects/ACL_Next/config/filesystem_authority.json",
            ).allowed
        )

    def test_read_is_separate_from_mutation_policy(self) -> None:
        service = self._windows_service()
        decision = service.evaluate(
            FilesystemOperation.READ,
            "C:/Windows/explorer.exe",
        )
        self.assertTrue(decision.allowed)

    def test_user_frozen_directory_is_recursive(self) -> None:
        service = self._windows_service()
        decision = service.evaluate(
            FilesystemOperation.CREATE,
            "C:/Frozen/releases/v1/output.txt",
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(str(decision.matched_protection.layer), "USER")

    def test_user_frozen_file_is_protected(self) -> None:
        service = self._windows_service()
        self.assertFalse(
            service.evaluate(
                FilesystemOperation.WRITE,
                "d:/knowngood/APP.EXE",
            ).allowed
        )

    def test_traversal_is_normalized_before_policy_check(self) -> None:
        service = self._windows_service()
        decision = service.evaluate(
            FilesystemOperation.WRITE,
            "C:/Safe/../Windows/explorer.exe",
        )
        self.assertFalse(decision.allowed)

    def test_relative_project_path_is_resolved_against_project_root(self) -> None:
        service = self._windows_service()
        decision = service.evaluate(
            FilesystemOperation.WRITE,
            "acl_core/authority/models.py",
        )
        self.assertFalse(decision.allowed)

    def test_move_checks_source_and_destination(self) -> None:
        service = self._windows_service()
        source_denied = service.evaluate(
            FilesystemOperation.MOVE,
            "C:/Frozen/file.txt",
            destination="C:/Work/file.txt",
        )
        destination_denied = service.evaluate(
            FilesystemOperation.MOVE,
            "C:/Work/file.txt",
            destination="C:/Frozen/file.txt",
        )
        self.assertFalse(source_denied.allowed)
        self.assertFalse(destination_denied.allowed)

    def test_move_requires_destination(self) -> None:
        service = self._windows_service()
        with self.assertRaises(CoreError):
            service.evaluate(FilesystemOperation.MOVE, "C:/Work/file.txt")

    def test_non_move_rejects_destination(self) -> None:
        service = self._windows_service()
        with self.assertRaises(CoreError):
            service.evaluate(
                FilesystemOperation.WRITE,
                "C:/Work/file.txt",
                destination="C:/Work/other.txt",
            )

    def test_require_allowed_raises_on_denied_mutation(self) -> None:
        service = self._windows_service()
        with self.assertRaises(CoreError) as captured:
            service.require_allowed(
                FilesystemOperation.WRITE,
                "C:/Windows/explorer.exe",
            )
        self.assertEqual(captured.exception.code, "FILESYSTEM_MUTATION_DENIED")

    def test_symlink_cannot_bypass_protected_target(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            frozen = root / "frozen"
            allowed = root / "allowed"
            frozen.mkdir()
            allowed.mkdir()
            link = allowed / "alias"
            try:
                link.symlink_to(frozen, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation is unavailable")

            service = FilesystemAuthorityService.for_acl(
                project_root=root,
                state_root=root / ".acl-state",
                authority_config_path=root / "config" / "filesystem_authority.json",
                user_protected_paths=((str(frozen), "operator-frozen directory"),),
                system_roots=(),
            )
            decision = service.evaluate(
                FilesystemOperation.WRITE,
                link / "nested.txt",
            )
            self.assertFalse(decision.allowed)


class FilesystemAuthorityConfigTests(unittest.TestCase):
    def _write_policy(self, config_root: Path, entries: list[dict]) -> Path:
        config_root.mkdir(parents=True, exist_ok=True)
        path = config_root / "filesystem_authority.json"
        path.write_text(
            json.dumps(
                {
                    "schema_version": "acl-filesystem-authority:v1",
                    "protected_paths": entries,
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_persistent_user_protection_is_loaded(self) -> None:
        with TemporaryDirectory() as directory:
            project = Path(directory)
            config = project / "config"
            state = project / ".acl-state"
            frozen = project / "saved-known-good"
            frozen.mkdir()
            policy = self._write_policy(
                config,
                [
                    {
                        "path": str(frozen),
                        "reason": "frozen by operator",
                    }
                ],
            )

            coordinator = FilesystemAuthorityCoordinator.create(
                project_root=project,
                state_root=state,
                config_root=config,
            )

            self.assertFalse(
                coordinator.evaluate(
                    FilesystemOperation.WRITE,
                    frozen / "app.py",
                ).allowed
            )
            self.assertTrue(
                coordinator.evaluate(
                    FilesystemOperation.WRITE,
                    project / "ordinary-project" / "app.py",
                ).allowed
            )
            self.assertFalse(
                coordinator.evaluate(
                    FilesystemOperation.WRITE,
                    policy,
                ).allowed
            )

    def test_controller_protects_installed_acl_packages(self) -> None:
        project = Path(__file__).resolve().parents[1]
        coordinator = FilesystemAuthorityCoordinator.create(
            project_root=project,
            state_root=project / ".acl-state-test",
            config_root=project / "config",
        )
        self.assertFalse(
            coordinator.evaluate(
                FilesystemOperation.WRITE,
                project / "acl_core" / "authority" / "filesystem.py",
            ).allowed
        )
        self.assertFalse(
            coordinator.evaluate(
                FilesystemOperation.WRITE,
                project / "acl_controller" / "service.py",
            ).allowed
        )

    def test_missing_policy_fails_closed_at_controller_startup(self) -> None:
        with TemporaryDirectory() as directory:
            project = Path(directory)
            config = project / "config"
            config.mkdir()
            with self.assertRaises(ControllerError) as captured:
                FilesystemAuthorityCoordinator.create(
                    project_root=project,
                    state_root=project / ".acl-state",
                    config_root=config,
                )
            self.assertEqual(
                captured.exception.code,
                "CONTROLLER_FILESYSTEM_AUTHORITY_MISSING",
            )

    def test_duplicate_user_paths_are_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            project = Path(directory)
            config = project / "config"
            frozen = project / "frozen"
            self._write_policy(
                config,
                [
                    {"path": str(frozen), "reason": "one"},
                    {"path": str(frozen).upper(), "reason": "duplicate"},
                ],
            )
            with self.assertRaises(ControllerError):
                FilesystemAuthorityCoordinator.create(
                    project_root=project,
                    state_root=project / ".acl-state",
                    config_root=config,
                )


if __name__ == "__main__":
    unittest.main()
