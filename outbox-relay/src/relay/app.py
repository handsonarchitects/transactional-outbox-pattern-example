from contextlib import asynccontextmanager

from fastapi import FastAPI
from . import logger
from .polling_publisher import PollingPublisher

publisher = PollingPublisher()

@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201, ARG001
    """https://fastapi.tiangolo.com/advanced/events/#lifespan."""
    logger.info("Outbox Relay: Starting up")
    await publisher.start()
    # FastAPI start excepting requests
    yield
    # FastAPI is shutting down
    logger.info("Outbox Relay: Shutting down")

    await publisher.stop()
    logger.info("Outbox Relay: Shut down complete")


app = FastAPI(lifespan=lifespan)

@app.get("/info")
async def info():
    result = await publisher.info()
    return {"info": result}