import json
import ipaddress
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, TypeAdapter, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.contracts import Credential


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: SecretStr = SecretStr("postgresql://peopleops:local@127.0.0.1:55433/peopleops_policy")
    auth_credentials: SecretStr = SecretStr("[]")
    llm_provider: Literal["mock", "openai_compatible", "qwen_local"] = "mock"
    embedding_provider: Literal["mock", "openai_compatible"] = "mock"
    provider_base_url: str = "https://api.openai.com/v1"
    provider_api_key: SecretStr = SecretStr("")
    llm_model: str = ""
    embedding_model: str = ""
    embedding_dimensions: int = Field(default=256, ge=8, le=4096)
    allow_external_provider: bool = False
    top_k: int = Field(default=5, ge=1, le=10)
    min_similarity: float = Field(default=0.18, ge=0, le=1)
    provider_timeout_seconds: float = Field(default=15, gt=0, le=60)
    n8n_webhook_url: str = "http://n8n:5678/webhook/peopleops-policy"
    policy_timezone: str = "UTC"

    @model_validator(mode="after")
    def validate_provider(self):
        if self.llm_provider == "qwen_local":
            url = urlsplit(self.provider_base_url)
            host = url.hostname or ""
            try:
                local = ipaddress.ip_address(host).is_loopback
            except ValueError:
                local = host in ("localhost", "host.docker.internal")
            if url.scheme != "http" or not local or url.username or url.password or url.query or url.fragment:
                raise ValueError("qwen_local requires a local HTTP endpoint, including host.docker.internal for Docker")
            if not self.llm_model:
                raise ValueError("LLM_MODEL is required for qwen_local")
        if "openai_compatible" in (self.llm_provider, self.embedding_provider):
            if not self.allow_external_provider:
                raise ValueError("Set ALLOW_EXTERNAL_PROVIDER=true to enable configured provider calls")
            if self.llm_provider == "openai_compatible" and not self.llm_model:
                raise ValueError("LLM_MODEL is required")
            if self.embedding_provider == "openai_compatible" and not self.embedding_model:
                raise ValueError("EMBEDDING_MODEL is required")
        self.credentials()
        return self

    def credentials(self) -> list[Credential]:
        credentials = TypeAdapter(list[Credential]).validate_python(json.loads(self.auth_credentials.get_secret_value()))
        if len({c.token_sha256 for c in credentials}) != len(credentials):
            raise ValueError("Duplicate identity tokens")
        return credentials

    @property
    def embedding_space(self) -> str:
        if self.embedding_provider == "mock":
            from app.providers import MOCK_VOCAB_HASH
            return f"mock-hash-v1:{MOCK_VOCAB_HASH}:{self.embedding_dimensions}"
        return f"{self.provider_base_url.rstrip('/')}:{self.embedding_model}:{self.embedding_dimensions}"
