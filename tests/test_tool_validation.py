import os
import stat

import pytest

from cassanova.core.tools.tool_validation import get_tool_path, is_tool_allowed


class TestIsToolAllowed:
    def test_allowed_tool_returns_true(self):
        allowed = ["nodetool", "sstabledump", "fqltool"]
        assert is_tool_allowed("nodetool", allowed_tools=allowed) is True

    def test_disallowed_tool_returns_false(self):
        allowed = ["nodetool", "sstabledump"]
        assert is_tool_allowed("rm", allowed_tools=allowed) is False

    def test_empty_string_returns_false(self):
        allowed = ["nodetool", "sstabledump"]
        assert is_tool_allowed("", allowed_tools=allowed) is False


class TestGetToolPath:
    def test_returns_path_for_existing_executable(self, tmp_path):
        tool_file = tmp_path / "mytool.exe"
        tool_file.write_text("fake")
        tool_file.chmod(tool_file.stat().st_mode | stat.S_IEXEC)
        result = get_tool_path("mytool.exe", tools_dir=str(tmp_path))
        assert result == str(tool_file)

    def test_returns_none_for_nonexistent_tool(self, tmp_path):
        result = get_tool_path("ghost_tool", tools_dir=str(tmp_path))
        assert result is None

    @pytest.mark.skipif(
        os.name == "nt",
        reason="Windows does not enforce executable permission via os.access",
    )
    def test_returns_none_for_non_executable(self, tmp_path):
        tool_file = tmp_path / "readonly_tool"
        tool_file.write_text("fake")
        tool_file.chmod(stat.S_IRUSR | stat.S_IWUSR)
        result = get_tool_path("readonly_tool", tools_dir=str(tmp_path))
        assert result is None
