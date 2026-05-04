from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    supabase_url: str
    supabase_service_role_key: str
    anthropic_api_key: str

    model_config = {"env_file": ".env"}

    @property
    def supabase_jwks_url(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"

settings = Settings()
