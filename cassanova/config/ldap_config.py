from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class LDAPConfig(BaseModel):
    enabled: bool = False
    server_uri: str = Field("ldap://localhost:389", description="LDAP Server URI (e.g., ldap://hostname:389 or ldaps://hostname:636)")
    bind_dn: Optional[str] = Field(None, description="DN to bind with for user search (Service Account). If None, anonymous bind is used.")
    bind_password: Optional[str] = Field(None, description="Password for bind_dn")
    base_dn: str = Field("dc=example,dc=com", description="Base DN to search for users")
    user_search_filter: str = Field("(uid={username})", description="Filter to find user by username. {username} placeholder will be replaced with input username.")
    
    group_search_base: Optional[str] = Field(None, description="Base DN to search for groups. If None, uses base_dn.")
    group_search_filter: str = Field("(member={user_dn})", description="Filter to find groups for a user. {user_dn} and {username} placeholders available.")
    group_name_attribute: str = Field("cn", description="Attribute of the group object that contains the group name")
    role_mapping: Dict[str, List[str]] = Field(default_factory=dict, description="Map LDAP group names to Cassanova roles. Key is LDAP group name, Value is list of Cassanova roles.")
    default_roles: List[str] = Field(default_factory=list, description="Roles assigned to all LDAP authenticated users if no groups match or map.")

    start_tls: bool = Field(False, description="Use StartTLS extension")
    ignore_cert_errors: bool = Field(False, description="Ignore SSL certificate errors (insecure)")
    
    email_attribute: Optional[str] = Field("mail", description="LDAP attribute for user email")
    full_name_attribute: Optional[str] = Field("cn", description="LDAP attribute for user full name")
