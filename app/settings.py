from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="db_", case_sensitive=False)

    host: str = "localhost"
    port: int = 5432
    user: str = "payments"
    password: str = "payments"
    name: str = "payments"

    pool_size: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 1800
    pool_pre_ping: bool = True

    @property
    def url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
        )


class RabbitMQSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="rabbitmq_", case_sensitive=False)

    url: str = "amqp://payments:payments@localhost:5672/"


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="app_", case_sensitive=False)

    api_key: str = "dev-secret-key"
    debug: bool = False
    outbox_poll_interval: float = 2.0


class ConsumerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="consumer_", case_sensitive=False)

    max_retries: int = 3
    base_delay_seconds: int = 5
    webhook_max_attempts: int = 3
    webhook_retry_min_wait: float = 2.0
    webhook_retry_max_wait: float = 8.0


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False)

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    rabbitmq: RabbitMQSettings = Field(default_factory=RabbitMQSettings)
    app: AppSettings = Field(default_factory=AppSettings)
    consumer: ConsumerSettings = Field(default_factory=ConsumerSettings)


settings = Settings()
