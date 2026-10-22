from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg://peopleops:peopleops_local_only@127.0.0.1:55432/peopleops_training"
    mock_url: str = "http://127.0.0.1:8801"
    api_url: str = "http://127.0.0.1:8800"
    llm_provider: str = "fake"
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = ""
    allow_external_llm: bool = False
