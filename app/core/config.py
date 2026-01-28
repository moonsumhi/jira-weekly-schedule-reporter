import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DOTENV = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "secret", ".env"  # core -> app
)


class Settings(BaseSettings):
    JIRA_BASE_URL: str = Field(..., description="https://moonsumhi.atlassian.net")
    JIRA_EMAIL: str = Field(..., description="Jira account email")
    JIRA_API_TOKEN: str = Field(..., description="Jira API token")
    MONGO_URI: str = Field(..., description="MongoDB URI")
    JWT_SECRET_KEY: str = Field(..., description="JWT Secret Key")
    JWT_ALGORITHM: str = Field(..., description="JWT Algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        ..., description="Access Token Expire Minutes"
    )
    APP_DB_NAME: str = Field(..., description="Mongo DB Name")
    CORS_ORIGINS: list[str] = Field(default=["http://localhost:9000"], description="Allowed CORS origins")

    PILOT_ENABLED: bool = Field(default=False, description="Enable Jira→Pilot polling")
    PILOT_GATEWAY_URL: str = Field(default="http://pilot:9090", description="Pilot gateway URL")
    PILOT_POLL_INTERVAL: int = Field(default=300, description="Polling interval in seconds")
    PILOT_LABEL: str = Field(default="pilot", description="Jira label to filter")

    model_config = SettingsConfigDict(
        env_file=DOTENV,
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()
