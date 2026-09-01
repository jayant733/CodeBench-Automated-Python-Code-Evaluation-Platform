import os
import shutil
import tempfile
from pathlib import Path


class AgentWorkspace:
    """Manages an isolated temporary workspace for an agent session."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        # Use a temporary directory for isolation
        self._temp_dir = tempfile.mkdtemp(prefix=f"agent_workspace_{session_id}_")
        self.root = Path(self._temp_dir).resolve()

    def get_path(self, relative_path: str) -> Path:
        """Resolve a path and ensure it stays within the workspace."""
        if os.path.isabs(relative_path):
            raise ValueError(f"Absolute paths are not allowed: {relative_path}")
        
        target = (self.root / relative_path).resolve()
        
        if not target.is_relative_to(self.root):
            raise ValueError(f"Path escape attempt blocked: {relative_path}")
            
        return target

    def cleanup(self) -> None:
        """Remove the workspace and all its contents."""
        try:
            shutil.rmtree(self.root)
        except Exception:
            pass  # Ignore cleanup errors (e.g. if files are locked)

    def __enter__(self) -> "AgentWorkspace":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.cleanup()
