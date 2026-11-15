"""Unit tests for BackupManager and FileTransaction.

Covers:
- $O(1)$ composite index lookup
- Metadata mtime cache synchronization
- FileTransaction context manager (commit, rollback, exception propagation)
- Integrity validation failure handling
- Double-fault chained exception handling
- Unified diff generation and file comparison
"""

import json
from pathlib import Path
import pytest

from sdlc_engine.session.backup_manager import BackupManager, FileTransaction
from sdlc_engine.shared.errors.exceptions import (
    BackupCreationError,
    IntegrityValidationError,
    RestoreError,
)


@pytest.fixture
def temp_workspace(tmp_path: Path):
    """Provide isolated temporary workspace and backup directories."""
    work_dir = tmp_path / "workspace"
    work_dir.mkdir(parents=True, exist_ok=True)
    backup_base = tmp_path / "backups"
    backup_base.mkdir(parents=True, exist_ok=True)
    return work_dir, backup_base


def test_backup_creation_and_composite_index(temp_workspace):
    """Verify backup creation populates the composite index for O(1) lookup."""
    work_dir, backup_base = temp_workspace
    sample_file = work_dir / "module.py"
    sample_file.write_text("def hello():\n    return 'world'\n", encoding="utf-8")

    manager = BackupManager("session_idx_01", backup_base_dir=str(backup_base))
    step_name = "Level 0 (Pre-Flight Sanity Guard)"

    success = manager.backup_file(str(sample_file), step_name, "initial state")
    assert success is True

    key = manager._canonical_key(str(sample_file), step_name)
    assert key in manager._index
    indexed_entry = manager._index[key]
    assert indexed_entry["original_path"] == str(sample_file.resolve())
    assert Path(indexed_entry["backup_path"]).exists()


def test_restore_file_from_index(temp_workspace):
    """Verify file restoration correctly restores original content using index."""
    work_dir, backup_base = temp_workspace
    sample_file = work_dir / "target.py"
    original_code = "ORIGINAL_DATA = 42\n"
    sample_file.write_text(original_code, encoding="utf-8")

    manager = BackupManager("session_restore_01", backup_base_dir=str(backup_base))
    step_name = "Phase 1"

    manager.backup_file(str(sample_file), step_name)

    sample_file.write_text("MUTATED_DATA = 999\n", encoding="utf-8")
    assert sample_file.read_text(encoding="utf-8") != original_code

    restored = manager.restore_file(str(sample_file), step_name)
    assert restored is True
    assert sample_file.read_text(encoding="utf-8") == original_code


def test_file_transaction_success(temp_workspace):
    """Verify FileTransaction commits changes when code inside block succeeds."""
    work_dir, backup_base = temp_workspace
    sample_file = work_dir / "script.py"
    sample_file.write_text("x = 10\n", encoding="utf-8")

    manager = BackupManager("session_tx_01", backup_base_dir=str(backup_base))
    step_name = "Step_Success"

    with manager.transaction(str(sample_file), step_name, "valid modification") as tx:
        assert isinstance(tx, FileTransaction)
        sample_file.write_text("x = 20\ny = 30\n", encoding="utf-8")

    assert sample_file.read_text(encoding="utf-8") == "x = 20\ny = 30\n"


def test_file_transaction_rollback_on_exception(temp_workspace):
    """Verify FileTransaction rolls back file and propagates exception without swallowing."""
    work_dir, backup_base = temp_workspace
    sample_file = work_dir / "script_fail.py"
    original_content = "def safe_function():\n    return True\n"
    sample_file.write_text(original_content, encoding="utf-8")

    manager = BackupManager("session_tx_fail", backup_base_dir=str(backup_base))
    step_name = "Step_Rollback"

    with pytest.raises(RuntimeError, match="Simulated crash"):
        with manager.transaction(str(sample_file), step_name):
            sample_file.write_text("BAD CONTENT THAT MUST BE REVERTED\n", encoding="utf-8")
            raise RuntimeError("Simulated crash")

    assert sample_file.read_text(encoding="utf-8") == original_content


def test_file_transaction_rollback_on_syntax_error(temp_workspace):
    """Verify FileTransaction triggers rollback and raises IntegrityValidationError on syntax defect."""
    work_dir, backup_base = temp_workspace
    sample_file = work_dir / "invalid_syntax.py"
    original_content = "VALID = True\n"
    sample_file.write_text(original_content, encoding="utf-8")

    manager = BackupManager("session_tx_syntax", backup_base_dir=str(backup_base))
    step_name = "Step_Syntax"

    with pytest.raises(IntegrityValidationError, match="File integrity validation failed"):
        with manager.transaction(str(sample_file), step_name):
            sample_file.write_text("def broken_syntax(:\n", encoding="utf-8")

    assert sample_file.read_text(encoding="utf-8") == original_content


def test_file_transaction_double_fault_chaining(temp_workspace, monkeypatch):
    """Verify FileTransaction raises chained RestoreError when rollback fails during exception."""
    work_dir, backup_base = temp_workspace
    sample_file = work_dir / "double_fault.py"
    sample_file.write_text("ORIGINAL = 1\n", encoding="utf-8")

    manager = BackupManager("session_double_fault", backup_base_dir=str(backup_base))
    step_name = "Step_DoubleFault"

    def faulty_restore(*args, **kwargs):
        raise OSError("Disk write error during rollback")

    monkeypatch.setattr(manager, "restore_file", faulty_restore)

    with pytest.raises(RestoreError, match="Double-fault during transaction rollback") as exc_info:
        with manager.transaction(str(sample_file), step_name):
            raise KeyError("Initial failure")

    assert isinstance(exc_info.value.__cause__, KeyError)


def test_metadata_mtime_synchronization(temp_workspace):
    """Verify BackupManager reloads metadata and index when metadata file mtime advances."""
    work_dir, backup_base = temp_workspace
    sample_file = work_dir / "sync_file.py"
    sample_file.write_text("VAL = 'old'\n", encoding="utf-8")

    manager1 = BackupManager("session_sync", backup_base_dir=str(backup_base))
    manager2 = BackupManager("session_sync", backup_base_dir=str(backup_base))

    manager1.backup_file(str(sample_file), "Step1", "backed up by proc1")

    key = manager2._canonical_key(str(sample_file), "Step1")
    manager2._ensure_metadata_sync()
    assert key in manager2._index


def test_generate_diff_and_compare_files(temp_workspace):
    """Verify diff generation and file comparison operations."""
    work_dir, backup_base = temp_workspace
    sample_file = work_dir / "diff_target.py"
    sample_file.write_text("line 1\nline 2\n", encoding="utf-8")

    manager = BackupManager("session_diff", backup_base_dir=str(backup_base))
    step_name = "DiffStep"

    manager.backup_file(str(sample_file), step_name)

    sample_file.write_text("line 1\nline 2 modified\nline 3 added\n", encoding="utf-8")

    diff_path = manager.generate_diff(str(sample_file), step_name)
    assert diff_path is not None
    assert Path(diff_path).exists()
    diff_text = Path(diff_path).read_text(encoding="utf-8")
    assert "+line 3 added" in diff_text

    comparison = manager.compare_files(str(sample_file), step_name)
    assert comparison["size_changed"] is True
    assert comparison["content_identical"] is False


def test_restore_nonexistent_backup(temp_workspace):
    """Verify restore_file returns False gracefully when no backup exists."""
    work_dir, backup_base = temp_workspace
    sample_file = work_dir / "untracked.py"
    sample_file.write_text("print('test')\n", encoding="utf-8")

    manager = BackupManager("session_empty", backup_base_dir=str(backup_base))
    assert manager.restore_file(str(sample_file), "NoStep") is False
