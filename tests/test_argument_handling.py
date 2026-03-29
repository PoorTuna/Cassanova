import os

import pytest

from cassanova.core.tools.argument_handling import parse_args, resolve_args


class TestParseArgs:
    def test_none_returns_empty(self):
        assert parse_args(None) == []

    def test_empty_string_returns_empty(self):
        assert parse_args("") == []

    def test_simple_args(self):
        assert parse_args("-a -b") == ["-a", "-b"]

    def test_quoted_args(self):
        assert parse_args('-a "hello world"') == ["-a", "hello world"]

    def test_single_arg(self):
        assert parse_args("--verbose") == ["--verbose"]


class TestResolveArgs:
    def test_nonexistent_path_returned_as_is(self, tmp_path):
        workdir = str(tmp_path)
        result = resolve_args(["nofile.txt"], workdir)
        assert result == ["nofile.txt"]

    def test_existing_file_resolved_to_absolute(self, tmp_path):
        target = tmp_path / "real.txt"
        target.write_text("data")
        workdir = str(tmp_path)
        result = resolve_args(["real.txt"], workdir)
        expected = os.path.abspath(os.path.join(workdir, "real.txt"))
        assert result == [expected]

    def test_path_traversal_blocked(self, tmp_path):
        workdir = str(tmp_path)
        with pytest.raises(ValueError, match="Illegal path"):
            resolve_args(["../../../etc/passwd"], workdir)
