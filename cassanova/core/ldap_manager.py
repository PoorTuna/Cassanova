from logging import getLogger
from typing import Optional, Any

try:
    import ldap

    LDAP_AVAILABLE = True
except ImportError:
    LDAP_AVAILABLE = False
    ldap = None

from cassanova.config.ldap_config import LDAPConfig
from cassanova.models.auth_models import WebUser

logger = getLogger(__name__)


class LDAPManager:
    def __init__(self, config: LDAPConfig):
        if not LDAP_AVAILABLE:
            raise ImportError("LDAP support is not available. Please install 'python-ldap'.")
        self.config = config

    def authenticate(self, username: str, password: str) -> Optional[WebUser]:
        if not username or not password:
            return None

        conn = None
        try:
            conn = self._initialize_connection()
            if not conn:
                return None

            if not self._bind_service(conn):
                return None

            user_dn = self._find_user_dn(conn, username)
            if not user_dn:
                return None

            if not self._verify_password(conn, user_dn, password, username):
                return None

            roles = self._get_roles(conn, user_dn, username)
            if self.config.default_roles:
                roles.extend(self.config.default_roles)

            roles = list(set(roles))

            return WebUser(
                username=username,
                password="",
                roles=roles
            )

        except Exception as e:
            logger.error(f"Error during LDAP authentication: {e}")
            return None
        finally:
            if conn:
                self._unbind_connection(conn)

    def _initialize_connection(self) -> Optional[Any]:
        try:
            conn = ldap.initialize(self.config.server_uri)
            conn.set_option(ldap.OPT_REFERRALS, 0)
            conn.set_option(ldap.OPT_PROTOCOL_VERSION, 3)

            if self.config.ignore_cert_errors:
                conn.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)

            if self.config.start_tls:
                conn.start_tls_s()

            return conn
        except ldap.LDAPError as e:
            logger.error(f"Failed to initialize LDAP connection: {e}")
            return None

    def _bind_service(self, conn) -> bool:
        try:
            if self.config.bind_dn and self.config.bind_password:
                conn.simple_bind_s(self.config.bind_dn, self.config.bind_password)
            else:
                conn.simple_bind_s()
            return True
        except ldap.INVALID_CREDENTIALS:
            logger.warning("Invalid bind credentials for LDAP service account")
        except ldap.LDAPError as e:
            logger.error(f"LDAP bind error: {e}")
        return False

    def _find_user_dn(self, conn, username: str) -> Optional[str]:
        search_filter = self.config.user_search_filter.replace("{username}", username)
        try:
            result = conn.search_s(
                self.config.base_dn,
                ldap.SCOPE_SUBTREE,
                search_filter,
                ['1.1']
            )
            if not result or not result[0]:
                logger.info(f"User {username} not found in LDAP")
                return None

            return result[0][0]
        except ldap.LDAPError as e:
            logger.warning(f"LDAP search failed: {e}")
            return None

    def _verify_password(self, conn, user_dn: str, password: str, username: str) -> bool:
        try:
            conn.simple_bind_s(user_dn, password)
            return True
        except ldap.INVALID_CREDENTIALS:
            logger.info(f"Invalid password for LDAP user {username}")
        except ldap.LDAPError as e:
            logger.error(f"LDAP user bind error: {e}")
        return False

    def _unbind_connection(self, conn):
        try:
            conn.unbind_s()
        except (ldap.LDAPError, Exception):
            pass

    def _get_roles(self, conn, user_dn: str, username: str) -> list[str]:
        roles = set()

        if self.config.group_search_base and self.config.group_search_filter:
            groups = self._search_groups(conn, user_dn, username)
            for grp_dn, grp_attrs in groups:
                if grp_dn:
                    roles.update(self._map_group_to_roles(grp_dn, grp_attrs))

        return list(roles)

    def _search_groups(self, conn, user_dn: str, username: str) -> list[tuple[str, dict[str, Any]]]:
        group_filter = self.config.group_search_filter.replace("{user_dn}", user_dn).replace("{username}", username)
        try:
            return conn.search_s(
                self.config.group_search_base,
                ldap.SCOPE_SUBTREE,
                group_filter,
                [self.config.group_name_attribute]
            )
        except ldap.LDAPError as e:
            logger.warning(f"LDAP group search failed: {e}")
            return []

    def _map_group_to_roles(self, grp_dn: str, grp_attrs: dict) -> list[str]:
        found_roles = set()
        grp_names = grp_attrs.get(self.config.group_name_attribute, [])
        grp_dn_lower = grp_dn.lower()

        for name_bytes in grp_names:
            name = name_bytes.decode('utf-8') if isinstance(name_bytes, bytes) else str(name_bytes)

            for map_key, map_roles in self.config.role_mapping.items():
                map_key_lower = map_key.lower()

                if name == map_key:
                    found_roles.update(map_roles)
                    continue

                if grp_dn_lower == map_key_lower:
                    found_roles.update(map_roles)
                    continue

                if grp_dn_lower.endswith("," + map_key_lower):
                    found_roles.update(map_roles)

        return list(found_roles)
