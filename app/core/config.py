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

    model_config = SettingsConfigDict(
        env_file=DOTENV,
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()
