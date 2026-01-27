from typing import Optional
from pydantic import BaseModel, Field, validator
from pathlib import Path


class TLSConfig(BaseModel):
    enabled: bool = False
    cert_file: Optional[str] = Field(None, description="Path to SSL certificate file (.crt or .pem)")
    key_file: Optional[str] = Field(None, description="Path to SSL private key file (.key or .pem)")
    ca_bundle: Optional[str] = Field(None, description="Optional: Path to CA certificate chain/bundle")
    
    min_tls_version: str = Field("TLSv1_2", description="Minimum TLS version: TLSv1_2 or TLSv1_3")
    enforce_https: bool = Field(True, description="Redirect HTTP to HTTPS")
    hsts_enabled: bool = Field(True, description="Enable HTTP Strict Transport Security")
    hsts_max_age: int = Field(31536000, description="HSTS max-age in seconds (default: 1 year)")
    hsts_include_subdomains: bool = Field(False, description="Apply HSTS to subdomains")
    
    @validator("cert_file", "key_file", "ca_bundle")
    def validate_file_path(cls, v):
        if v is not None and not Path(v).exists():
            raise ValueError(f"File not found: {v}")
        return v
    
    @validator("min_tls_version")
    def validate_tls_version(cls, v):
        allowed = ["TLSv1_2", "TLSv1_3"]
        if v not in allowed:
            raise ValueError(f"min_tls_version must be one of: {allowed}")
        return v
    
    def validate_tls_files(self):
        if self.enabled:
            if not self.cert_file:
                raise ValueError("TLS enabled but cert_file not provided")
            if not self.key_file:
                raise ValueError("TLS enabled but key_file not provided")
