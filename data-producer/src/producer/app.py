from contextlib import asynccontextmanager

from fastapi import FastAPI
from . import logger
from .items_producer import ItemsProducer

producer = ItemsProducer()

@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201, ARG001
    """https://fastapi.tiangolo.com/advanced/events/#lifespan."""
    logger.info("Auction Items Data Producer: Starting up")
    await producer.start()
    # FastAPI start excepting requests
    yield
    # FastAPI is shutting down
    logger.info("Auction Items Data Producer: Shutting down")

    await producer.stop()
    logger.info("Auction Items Data Producer: Shut down complete")


app = FastAPI(lifespan=lifespan)

@app.get("/add-items/{count}")
async def new_items(count: int):
    result = await producer.generate_items(count)
    return {"status": "ok", "items": result}

@app.get("/info")
async def info():
    result = await producer.info()
    return {"info": result}