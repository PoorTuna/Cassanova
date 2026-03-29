from cassanova.core.ldap_manager import _ldap_escape


class TestLdapEscape:
    def test_no_special_chars(self):
        assert _ldap_escape("alice") == "alice"

    def test_escapes_backslash(self):
        assert _ldap_escape("a\\b") == "a\\5cb"

    def test_escapes_asterisk(self):
        assert _ldap_escape("user*") == "user\\2a"

    def test_escapes_open_paren(self):
        assert _ldap_escape("user(1)") == "user\\281\\29"

    def test_escapes_close_paren(self):
        assert _ldap_escape("user)") == "user\\29"

    def test_escapes_null_byte(self):
        assert _ldap_escape("user\x00") == "user\\00"

    def test_injection_attempt_escaped(self):
        result = _ldap_escape("*)(&")
        assert "*" not in result
        assert "(" not in result
        assert ")" not in result
        assert "\\2a" in result
        assert "\\28" in result
        assert "\\29" in result

    def test_complex_injection(self):
        result = _ldap_escape("admin)(|(uid=*))")
        assert "(" not in result
        assert ")" not in result
        assert "*" not in result

    def test_backslash_escaped_first(self):
        result = _ldap_escape("\\*")
        assert result == "\\5c\\2a"
