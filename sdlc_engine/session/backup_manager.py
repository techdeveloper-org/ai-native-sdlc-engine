"""File Backup and Restore System.

Provides safe backup and restore functionality with:
- Before/after file comparison
- Atomic rollback on failure
- Unified diff generation
- Transaction semantics via FileTransaction context manager
- $O(1)$ composite index lookup for backup entries
"""

import difflib
import json
import os
import re
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sdlc_engine.shared.config.claude_paths import get_claude_logs_dir
from sdlc_engine.shared.errors.exceptions import (
    BackupCreationError,
    IntegrityValidationError,
    RestoreError,
)
from sdlc_engine.shared.logging.logger_factory import get_logger

logger = get_logger(__name__)


class FileTransaction:
    """Atomic file modification context manager with rollback semantics.

    Implements the Memento pattern for safe in-place file modifications.
    Captures file state on entry and automatically rolls back on exception
    or integrity validation failure.
    """

    def __init__(
        self,
        backup_manager: "BackupManager",
        file_path: str,
        step: str,
        description: str = "",
    ) -> None:
        """Initialize file transaction.

        Args:
            backup_manager: Active BackupManager instance.
            file_path: Path to file to modify within transaction.
            step: Pipeline step/phase name.
            description: Optional description of intended modification.
        """
        self.backup_manager = backup_manager
        self.file_path = str(Path(file_path).resolve())
        self.step = step
        self.description = description
        self._backup_succeeded = False

    def __enter__(self) -> "FileTransaction":
        """Enter transaction context: capture atomic backup before modification.

        Returns:
            The active FileTransaction instance.

        Raises:
            BackupCreationError: If the pre-transaction backup could not be created.
        """
        self._backup_succeeded = self.backup_manager.backup_file(
            self.file_path, self.step, self.description
        )
        if not self._backup_succeeded:
            raise BackupCreationError(
                f"Pre-transaction backup failed for {self.file_path}"
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit transaction context with rollback on failure or integrity check.

        Args:
            exc_type: Exception class if an exception was raised inside the block.
            exc_val: Exception instance if an exception was raised inside the block.
            exc_tb: Traceback object if an exception was raised inside the block.

        Returns:
            False to guarantee exception propagation.

        Raises:
            RestoreError: If rollback fails during an active exception (double-fault).
            IntegrityValidationError: If block succeeded but file integrity check failed.
        """
        if exc_type is not None:
            try:
                restored = self.backup_manager.restore_file(self.file_path, self.step)
                if not restored:
                    raise RestoreError(
                        f"Rollback failed for {self.file_path} during exception handling"
                    ) from exc_val
            except Exception as restore_exc:
                if not isinstance(restore_exc, RestoreError):
                    raise RestoreError(
                        f"Double-fault during transaction rollback for {self.file_path}: {restore_exc}"
                    ) from exc_val
                raise

            return False

        if not self.backup_manager.validate_file_integrity(self.file_path, self.step):
            try:
                restored = self.backup_manager.restore_file(self.file_path, self.step)
                if not restored:
                    raise RestoreError(
                        f"File integrity failed and rollback returned False for {self.file_path}"
                    )
            except Exception as restore_exc:
                if not isinstance(restore_exc, RestoreError):
                    raise RestoreError(
                        f"File integrity failed and rollback failed for {self.file_path}: {restore_exc}"
                    ) from restore_exc
                raise
            raise IntegrityValidationError(
                f"File integrity validation failed post-transaction for {self.file_path}"
            )

        return False


class BackupManager:
    """Manages file backups, indexing, diffing, and rollback operations."""

    def __init__(self, session_id: str, backup_base_dir: Optional[str] = None) -> None:
        """Initialize backup manager for a session.

        Args:
            session_id: Unique session identifier.
            backup_base_dir: Base directory for backups. Defaults to the
                Claude logs root resolved by path_resolver.
        """
        self.session_id = session_id
        self._lock = threading.Lock()
        base = Path(backup_base_dir).expanduser() if backup_base_dir else get_claude_logs_dir()
        self.backup_dir = base / "sessions" / session_id / "backup"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self.diff_dir = self.backup_dir / "diffs"
        self.diff_dir.mkdir(parents=True, exist_ok=True)

        self.metadata_file = self.backup_dir / "backup_metadata.json"
        self._metadata_mtime: float = 0.0
        self._index: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self.metadata = self._load_metadata()
        self._rebuild_index()

    @staticmethod
    def _canonical_key(file_path: str, step: str) -> Tuple[str, str]:
        """Generate canonical normalized key for backup indexing.

        Args:
            file_path: Original file path string.
            step: Step name string.

        Returns:
            Tuple of canonical resolved path and step name.
        """
        try:
            resolved = str(Path(file_path).resolve())
        except Exception:
            resolved = str(Path(file_path))
        return (resolved, str(step))

    def _rebuild_index(self) -> None:
        """Rebuild composite (path, step) index pointing to the latest backup entry."""
        new_index: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for entry in sorted(
            self.metadata.get("backups", []),
            key=lambda x: x.get("timestamp", ""),
        ):
            key = self._canonical_key(entry["original_path"], entry["step"])
            new_index[key] = entry
        self._index = new_index

    def _ensure_metadata_sync(self) -> None:
        """Ensure memory state is synchronized with on-disk metadata mtime."""
        if self.metadata_file.exists():
            try:
                current_mtime = self.metadata_file.stat().st_mtime
                if current_mtime != self._metadata_mtime:
                    self.metadata = self._load_metadata()
                    self._rebuild_index()
            except OSError as err:
                logger.debug("Failed checking metadata file mtime: %s", err)

    def transaction(
        self, file_path: str, step: str, description: str = ""
    ) -> FileTransaction:
        """Create a FileTransaction context manager for atomic modifications.

        Args:
            file_path: Path to target file.
            step: Step/phase name.
            description: Optional intent description.

        Returns:
            FileTransaction context manager.
        """
        return FileTransaction(self, file_path, step, description)

    def backup_file(self, file_path: str, step: str, description: str = "") -> bool:
        """Create backup of a file before modification.

        Args:
            file_path: Path to file to backup.
            step: Step/phase name (e.g., 'Level 0 (Pre-Flight Sanity Guard)').
            description: Optional description of what's being done.

        Returns:
            True if backup successful, False otherwise.
        """
        target_path = Path(file_path)

        if not target_path.exists():
            logger.warning(
                "File not found for backup: %s",
                file_path,
                extra={"file_path": str(file_path), "step": step},
            )
            return False

        try:
            with self._lock:
                self._ensure_metadata_sync()
                clean_step = re.sub(r"[^A-Za-z0-9_\-]", "_", step)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                unique_suffix = uuid.uuid4().hex[:6]
                safe_name = f"{target_path.stem}_{timestamp}_{unique_suffix}{target_path.suffix}"
                backup_file = self.backup_dir / f"{clean_step}_{safe_name}"

                tmp_token = f"{os.getpid()}_{threading.get_ident()}_{uuid.uuid4().hex[:8]}"
                tmp_backup = backup_file.with_name(f".{backup_file.name}.tmp.{tmp_token}")
                try:
                    tmp_backup.write_bytes(target_path.read_bytes())
                    os.replace(tmp_backup, backup_file)
                finally:
                    if tmp_backup.exists():
                        try:
                            tmp_backup.unlink()
                        except OSError:
                            pass

                entry = {
                    "timestamp": datetime.now().isoformat(),
                    "original_path": str(target_path.resolve()),
                    "backup_path": str(backup_file.resolve()),
                    "step": step,
                    "description": description,
                    "file_size": target_path.stat().st_size,
                }

                self.metadata["backups"].append(entry)
                key = self._canonical_key(str(target_path), step)
                self._index[key] = entry
                self._save_metadata()

            logger.info(
                "Backup created successfully: %s -> %s",
                file_path,
                backup_file,
                extra={
                    "original_path": str(file_path),
                    "backup_path": str(backup_file),
                    "step": step,
                },
            )
            return True

        except Exception as e:
            logger.error(
                "Backup failed for %s: %s",
                file_path,
                e,
                exc_info=True,
                extra={"file_path": str(file_path), "step": step},
            )
            return False

    def restore_file(self, file_path: str, step: str) -> bool:
        """Restore file from backup using composite index lookup.

        Args:
            file_path: Path to file to restore.
            step: Step name to find corresponding backup.

        Returns:
            True if restore successful, False otherwise.
        """
        target_path = Path(file_path)

        try:
            with self._lock:
                self._ensure_metadata_sync()
                key = self._canonical_key(str(target_path), step)
                latest_backup = self._index.get(key)

                if not latest_backup:
                    logger.warning(
                        "No backup found for %s in step %s",
                        file_path,
                        step,
                        extra={"file_path": str(file_path), "step": step},
                    )
                    return False

                backup_file = Path(latest_backup["backup_path"])

                if not backup_file.exists():
                    logger.error(
                        "Backup file not found on disk: %s",
                        backup_file,
                        extra={"backup_file": str(backup_file), "file_path": str(file_path)},
                    )
                    return False

                tmp_token = f"{os.getpid()}_{threading.get_ident()}_{uuid.uuid4().hex[:8]}"
                tmp_restore = target_path.with_name(f".{target_path.name}.tmp.{tmp_token}")
                try:
                    tmp_restore.write_bytes(backup_file.read_bytes())
                    os.replace(tmp_restore, target_path)
                finally:
                    if tmp_restore.exists():
                        try:
                            tmp_restore.unlink()
                        except OSError:
                            pass

                latest_backup["restored"] = True
                latest_backup["restore_timestamp"] = datetime.now().isoformat()
                self._save_metadata()

            logger.info(
                "Restored: %s from %s",
                file_path,
                backup_file,
                extra={"file_path": str(file_path), "backup_file": str(backup_file)},
            )
            return True

        except Exception as e:
            logger.error(
                "Restore failed for %s: %s",
                file_path,
                e,
                exc_info=True,
                extra={"file_path": str(file_path), "step": step},
            )
            return False

    def generate_diff(self, file_path: str, step: str, label: str = "") -> Optional[str]:
        """Generate unified diff between original and current file.

        Args:
            file_path: Path to file.
            step: Step name.
            label: Custom label for diff file.

        Returns:
            Path to diff file, or None if error.
        """
        target_path = Path(file_path)

        try:
            self._ensure_metadata_sync()
            key = self._canonical_key(str(target_path), step)
            latest_backup = self._index.get(key)

            if not latest_backup:
                logger.warning(
                    "No backup found for diff generation: %s (step: %s)",
                    file_path,
                    step,
                    extra={"file_path": str(file_path), "step": step},
                )
                return None

            backup_file = Path(latest_backup["backup_path"])

            try:
                original_lines = backup_file.read_text(encoding="utf-8").splitlines(keepends=True)
            except Exception:
                original_lines = (
                    backup_file.read_bytes()
                    .decode("utf-8", errors="replace")
                    .splitlines(keepends=True)
                )

            try:
                current_lines = target_path.read_text(encoding="utf-8").splitlines(keepends=True)
            except Exception:
                current_lines = (
                    target_path.read_bytes()
                    .decode("utf-8", errors="replace")
                    .splitlines(keepends=True)
                )

            diff_lines = difflib.unified_diff(
                original_lines,
                current_lines,
                fromfile=f"{target_path} (original)",
                tofile=f"{target_path} (current)",
                lineterm="",
            )

            diff_content = "\n".join(diff_lines)

            diff_label = label or target_path.stem
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            diff_filename = f"{step}_{diff_label}_{timestamp_str}.diff"
            diff_file = self.diff_dir / diff_filename

            tmp_diff = diff_file.with_name(f".{diff_file.name}.tmp.{os.getpid()}")
            tmp_diff.write_text(diff_content, encoding="utf-8")
            os.replace(tmp_diff, diff_file)

            logger.info(
                "Diff generated successfully: %s",
                diff_file,
                extra={"diff_file": str(diff_file), "file_path": str(file_path)},
            )
            return str(diff_file)

        except Exception as e:
            logger.error(
                "Diff generation failed for %s: %s",
                file_path,
                e,
                exc_info=True,
                extra={"file_path": str(file_path), "step": step},
            )
            return None

    def validate_file_integrity(self, file_path: str, step: str) -> bool:
        """Validate that file was not corrupted during modification.

        Args:
            file_path: Path to file to validate.
            step: Step name.

        Returns:
            True if file is valid, False otherwise.
        """
        target_path = Path(file_path)

        if not target_path.exists():
            logger.error(
                "File not found for integrity validation: %s",
                file_path,
                extra={"file_path": str(file_path), "step": step},
            )
            return False

        try:
            content = target_path.read_text(encoding="utf-8")

            if not content.strip():
                logger.warning(
                    "File is empty after modification: %s",
                    file_path,
                    extra={"file_path": str(file_path), "step": step},
                )
                return False

            if target_path.suffix == ".py":
                try:
                    compile(content, str(target_path), "exec")
                except SyntaxError as e:
                    logger.error(
                        "Syntax error detected in %s: %s",
                        file_path,
                        e,
                        extra={"file_path": str(file_path), "error": str(e)},
                    )
                    return False

            logger.info(
                "File integrity validation passed: %s",
                file_path,
                extra={"file_path": str(file_path), "step": step},
            )
            return True

        except Exception as e:
            logger.error(
                "File validation failed for %s: %s",
                file_path,
                e,
                exc_info=True,
                extra={"file_path": str(file_path), "step": step},
            )
            return False

    def compare_files(self, file_path: str, step: str) -> Dict[str, Any]:
        """Get detailed comparison between original backup and current file.

        Args:
            file_path: Path to file.
            step: Step name.

        Returns:
            Dict with comparison details.
        """
        target_path = Path(file_path)

        try:
            self._ensure_metadata_sync()
            key = self._canonical_key(str(target_path), step)
            latest_backup = self._index.get(key)

            if not latest_backup:
                return {"error": "No backup found", "file": str(file_path)}

            backup_file = Path(latest_backup["backup_path"])

            original_content = backup_file.read_bytes()
            current_content = target_path.read_bytes()

            return {
                "file": str(file_path),
                "original_size": len(original_content),
                "current_size": len(current_content),
                "size_changed": len(original_content) != len(current_content),
                "content_identical": original_content == current_content,
                "backup_path": str(backup_file),
            }

        except Exception as e:
            return {"error": str(e), "file": str(file_path)}

    def get_backup_history(self, file_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get backup history for a file or all files.

        Args:
            file_path: Optional file path to filter.

        Returns:
            List of backup entries sorted in descending chronological order.
        """
        self._ensure_metadata_sync()
        backups = self.metadata.get("backups", [])

        if file_path:
            resolved_target = str(Path(file_path).resolve())
            backups = [
                b for b in backups if str(Path(b["original_path"]).resolve()) == resolved_target
            ]

        return sorted(backups, key=lambda x: x.get("timestamp", ""), reverse=True)

    def _load_metadata(self) -> Dict[str, Any]:
        """Load or initialize metadata from disk."""
        if self.metadata_file.exists():
            try:
                data = json.loads(self.metadata_file.read_text(encoding="utf-8"))
                self._metadata_mtime = self.metadata_file.stat().st_mtime
                return data
            except (OSError, ValueError) as exc:
                logger.debug("Could not load backup metadata, starting fresh: %s", exc)

        self._metadata_mtime = 0.0
        return {
            "session_id": self.session_id,
            "created": datetime.now().isoformat(),
            "backups": [],
        }

    def _save_metadata(self) -> None:
        """Save metadata to file atomically."""
        tmp_token = f"{os.getpid()}_{threading.get_ident()}_{uuid.uuid4().hex[:8]}"
        tmp_meta = self.metadata_file.with_name(
            f".{self.metadata_file.name}.tmp.{tmp_token}"
        )
        try:
            tmp_meta.write_text(json.dumps(self.metadata, indent=2), encoding="utf-8")
            os.replace(tmp_meta, self.metadata_file)
            self._metadata_mtime = self.metadata_file.stat().st_mtime
        except Exception as e:
            logger.error("Failed to save backup metadata: %s", e, exc_info=True)
        finally:
            if tmp_meta.exists():
                try:
                    tmp_meta.unlink()
                except OSError:
                    pass


def create_backup_manager(session_id: str) -> BackupManager:
    """Create a new backup manager instance.

    Args:
        session_id: Unique session ID.

    Returns:
        BackupManager instance.
    """
    return BackupManager(session_id)
