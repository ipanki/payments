import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.api.router import router
from app.container import container

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await container.init_resources()  # type: ignore[misc]
    container.wire(packages=["app.api"])

    publisher = await container.outbox_publisher.async_()
    publisher.start()
    logger.info("API service started")

    yield

    await publisher.stop()
    await container.shutdown_resources()  # type: ignore[misc]
    logger.info("API service stopped")


app = FastAPI(
    title="Payments Service",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(router)


def run() -> None:
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    run()
