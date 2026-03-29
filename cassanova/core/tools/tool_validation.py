import os

from cassanova.consts.cass_tools import CassTools


def is_tool_allowed(tool: str, allowed_tools: tuple[str, ...] = CassTools.ALLOWED_TOOLS) -> bool:
    return tool in allowed_tools


def get_tool_path(tool: str, tools_dir: str = CassTools.TOOLS_DIR) -> str | None:
    path = os.path.join(tools_dir, tool)
    return path if os.path.isfile(path) and os.access(path, os.X_OK) else None
