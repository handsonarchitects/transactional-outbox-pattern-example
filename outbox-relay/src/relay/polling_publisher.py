import json
import os
from datetime import datetime
from typing import Any

import aio_pika
import aiofiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from elasticsearch import AsyncElasticsearch

from . import logger

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
QUEUE_NAME = "items-updates"

ES_HOST = os.environ.get("ES_HOST", "http://elasticsearch:9200")
INDEX_NAME = "auction_items"

POLLING_LIMIT = int(os.getenv("POLLING_LIMIT", 3))
POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", 5))

STATE_PATH = os.getenv("STATE_PATH", "/app/state_polling.json")


class PollingPublisher:
    connection: aio_pika.Connection
    channel: aio_pika.Channel
    exchange: aio_pika.Exchange
    scheduler = AsyncIOScheduler()
    es = AsyncElasticsearch(ES_HOST)
    items_processed: int = 0
    last_update: datetime = None

    async def start(self) -> None:
        logger.info("Starting Polling Publisher")
        self.connection = await aio_pika.connect_robust(RABBITMQ_URL)
        self.channel = await self.connection.channel()
        self.exchange = await self.channel.declare_exchange(
            "items-updates", aio_pika.ExchangeType.FANOUT, durable=True
        )
        await self.load_state()

        self.scheduler.add_job(
            self.process_outbox, "interval", seconds=POLLING_INTERVAL
        )
        self.scheduler.start()

    async def stop(self) -> None:
        """Stops the processor."""
        logger.info("Stopping Polling Publisher")
        await self.save_state()
        await self.channel.close()
        await self.connection.close()
        await self.es.close()
        await self.scheduler.shutdown()

    async def process_outbox(self):
        """Fetches jobs from Elasticsearch and sends updates to RabbitMQ."""
        query = {
            "query": {"term": {"outbox_sent": False}},
            "sort": [{"created_at": "asc"}],
            "size": POLLING_LIMIT,
        }
        res = await self.es.search(index=INDEX_NAME, body=query)

        for hit in res["hits"]["hits"]:
            id = hit["_id"]
            source = hit["_source"]
            title = source.get("title")
            created_at = source.get("created_at")

            message_body = json.dumps(
                {"id": id, "title": title, "created_at": created_at}
            ).encode()

            try:
                await self.publish_event(message_body)

                # Mark the job as published by updating the outbox_sent flag
                await self.es.update(
                    index=INDEX_NAME, id=id, body={"doc": {"outbox_sent": True}}
                )
                logger.info(f"Marked item {id} as published.")
                self.items_processed += 1
                self.last_update = datetime.now()
                await self.save_state()
            except Exception as e:
                logger.error(f"Failed to publish item {id}: {e}")

    async def save_state(self) -> None:
        """Persists the current state asynchronously."""
        state = {
            "items_processed": self.items_processed,
            "last_update": self.last_update.isoformat() if self.last_update else None,
        }
        try:
            async with aiofiles.open(STATE_PATH, "w") as f:
                await f.write(json.dumps(state))
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    async def load_state(self) -> None:
        """Loads the saved state asynchronously if available."""
        if os.path.exists(STATE_PATH):
            try:
                async with aiofiles.open(STATE_PATH, "r") as f:
                    content = await f.read()
                    state = json.loads(content)
                    self.items_processed = state.get("items_processed", 0)
                    self.last_update = (
                        datetime.fromisoformat(state["last_update"])
                        if state["last_update"]
                        else None
                    )
                    logger.info(f"State loaded asynchronously: {state}")
            except Exception as e:
                logger.error(f"Failed to load state: {e}")
        else:
            logger.info("No previous state found, starting fresh.")

    async def publish_event(self, message_body):
        await self.exchange.publish(
            aio_pika.Message(
                body=message_body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key="",
            mandatory=True,
        )
        logger.info(f"Published event: {message_body}")

    async def info(self) -> dict[str, Any]:
        return {
            "items_processed": self.items_processed,
            "last_update": self.last_update,
        }
