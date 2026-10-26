from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    app_name: str = "service"
    # DEBUG is also set by some shells/tools to non-boolean values.
    debug: bool = Field(default=False, validation_alias="APP_DEBUG")

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=False,
    )
