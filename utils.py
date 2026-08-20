import os
import re
import zipfile
from pathlib import Path
import board

BASE_DIR = Path(__file__).resolve().parent
BOARD_PATH = Path(os.environ.get("BOARD_PATH", BASE_DIR / "board.sqlite"))
WORKSPACE_DIR = Path(os.environ.get("WORKSPACE_DIR", BASE_DIR / "workspace"))


def extract_localhost_url(text: str) -> str:
    """Detect if a local HTTP server URL was produced in output logs."""
    match = re.search(r"http://(?:localhost|127\.0\.0\.1):\d+[^\s]*", str(text))
    return match.group(0) if match else ""


def generate_workspace_zip() -> str:
    """Create a zip archive of the workspace directory for download."""
    zip_path = BASE_DIR / "workspace.zip"
    if not WORKSPACE_DIR.exists():
        return ""
        
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(WORKSPACE_DIR):
            for file in files:
                file_path = Path(root) / file
                zipf.write(file_path, file_path.relative_to(WORKSPACE_DIR))
    return str(zip_path) if zip_path.exists() else ""


def format_board_progress() -> str:
    """Format active SQLite board state into markdown for the collapsible step block."""
    if not BOARD_PATH.exists():
        return "Initializing workspace database..."
        
    todos = board.list_todos(BOARD_PATH)
    if not todos:
        return "Planning execution breakdown..."
        
    md_lines = []
    for item in todos:
        status = item.get("status", "pending")
        role = item.get("role", "Worker")
        task = item.get("task", "")
        
        if status == "done":
            icon = "✅"
        elif status == "in_progress":
            icon = "⏳"
        else:
            icon = "⚪"
            
        md_lines.append(f"- {icon} **[{role.upper()}]** {task}")
        
    return "\n".join(md_lines)


def reset_conversation():
    """Reset board state and return cleared Gradio state."""
    board.reset_board(BOARD_PATH)
    return [], None, ""