from contextlib import asynccontextmanager

from fastapi import FastAPI
from . import logger
from .items_consumer import ItemsConsumer

consumer = ItemsConsumer()

@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201, ARG001
    """https://fastapi.tiangolo.com/advanced/events/#lifespan."""
    logger.info("Auction Items Consumer: Starting up")
    await consumer.start()
    # FastAPI start excepting requests
    yield
    # FastAPI is shutting down
    logger.info("Auction Items Consumer: Shutting down")

    await consumer.stop()
    logger.info("Auction Items Consumer: Shut down complete")


app = FastAPI(lifespan=lifespan)

@app.get("/list-items")
async def list_items():
    result = await consumer.get_items()
    return {"items": result}

@app.get("/info")
async def info():
    result = await consumer.info()
    return {"info": result}
