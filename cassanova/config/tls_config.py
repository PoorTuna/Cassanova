from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class TLSConfig(BaseModel):
    enabled: bool = False
    cert_file: str | None = Field(None, description="Path to SSL certificate file (.crt or .pem)")
    key_file: str | None = Field(None, description="Path to SSL private key file (.key or .pem)")
    ca_bundle: str | None = Field(None, description="Optional: Path to CA certificate chain/bundle")

    min_tls_version: str = Field("TLSv1_2", description="Minimum TLS version: TLSv1_2 or TLSv1_3")
    enforce_https: bool = Field(True, description="Redirect HTTP to HTTPS")
    hsts_enabled: bool = Field(True, description="Enable HTTP Strict Transport Security")
    hsts_max_age: int = Field(31536000, description="HSTS max-age in seconds (default: 1 year)")
    hsts_include_subdomains: bool = Field(False, description="Apply HSTS to subdomains")

    @field_validator("cert_file", "key_file", "ca_bundle", mode="before")
    @classmethod
    def validate_file_path(cls, v: str | None) -> str | None:
        if v is not None and not Path(v).exists():
            raise ValueError(f"File not found: {v}")
        return v

    @field_validator("min_tls_version", mode="before")
    @classmethod
    def validate_tls_version(cls, v: str) -> str:
        allowed = ["TLSv1_2", "TLSv1_3"]
        if v not in allowed:
            raise ValueError(f"min_tls_version must be one of: {allowed}")
        return v

    def validate_tls_files(self) -> None:
        if self.enabled:
            if not self.cert_file:
                raise ValueError("TLS enabled but cert_file not provided")
            if not self.key_file:
                raise ValueError("TLS enabled but key_file not provided")
