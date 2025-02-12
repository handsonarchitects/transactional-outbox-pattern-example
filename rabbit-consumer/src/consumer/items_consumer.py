import json
import asyncio
import os
from datetime import datetime
from typing import Any

import aio_pika
import aiofiles

from . import logger

RABBITMQ_URL = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
QUEUE_NAME = "items-updates"

STATE_PATH = os.getenv("STATE_PATH", "./state.json")  # State file path


class ItemsConsumer:
    connection: aio_pika.Connection
    channel: aio_pika.Channel
    items: dict[str, Any] = {}
    last_update: datetime = None
    subscribe_task: asyncio.Task | None = None

    async def start(self) -> None:
        logger.info("Starting Items Consumer")
        await self.load_state()

        self.connection = await aio_pika.connect_robust(RABBITMQ_URL)
        self.channel = await self.connection.channel()
        exchange = await self.channel.declare_exchange(
            "items-updates", aio_pika.ExchangeType.FANOUT, durable=True
        )

        arguments = {"x-queue-type": "quorum"}
        queue = await self.channel.declare_queue(
            "consumer", durable=True, arguments=arguments
        )
        await queue.bind(exchange, routing_key="")
        logger.info(" [*] Waiting for messages...")
        self.subscribe_task = asyncio.create_task(self.subscribe(queue))

    async def stop(self) -> None:
        """Stops the processor."""
        logger.info("Stopping Items Consumer")
        
        # Cancel the subscription task if it exists.
        if self.subscribe_task:
            self.subscribe_task.cancel()
            try:
                await self.subscribe_task
            except asyncio.CancelledError:
                logger.info("Subscription task cancelled.")
        
        await self.save_state()
        await self.channel.close()
        await self.connection.close()
        
    async def subscribe(self, queue: aio_pika.Queue):
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        logger.debug(f"Received headers: {message.headers}")
                        await self.on_message(message.body)
                    except Exception as e:  # noqa: BLE001
                        logger.error(f"Error processing message: {e}")
                        await message.reject(requeue=True)
        logger.info(" [*] Waiting for messages...")

    async def on_message(self, message: str):
        data = json.loads(message)
        logger.info(f"Received data: {data}")
        self.items[data.get("id")] = {
            "title": data.get("title"),
            "created_at": data.get("created_at"),
        }
        self.last_update = datetime.now()
        await self.save_state()

    async def get_items(self) -> list[str]:
        return list(self.items.values())

    async def info(self) -> dict[str, Any]:
        return {
            "items_consumed": len(self.items),
            "last_update": self.last_update,
        }

    async def save_state(self) -> None:
        """Persists the current state asynchronously, including all items."""
        state = {
            "items": self.items,
            "last_update": self.last_update.isoformat() if self.last_update else None
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
                    self.items = state.get("items", {})
                    self.last_update = (
                        datetime.fromisoformat(state["last_update"])
                        if state["last_update"] else None
                    )
                    logger.info(f"State loaded asynchronously with {len(self.items)} items.")
            except Exception as e:
                logger.error(f"Failed to load state: {e}")
        else:
            logger.info("No previous state found, starting fresh.")
