from typing import Any
import uuid
import os
import random
import asyncio
import aiofiles
import json
from elasticsearch import AsyncElasticsearch
from . import logger
from datetime import datetime

STATE_PATH = os.getenv("STATE_PATH", "/app/state.json")

ES_HOST = os.environ.get("ES_HOST", "http://elasticsearch:9200")
INDEX_NAME = "auction_items"

class ItemsProducer:
    
    es: AsyncElasticsearch
    last_update: datetime = None
    items_produced: int = 0
    
    async def start(self) -> None:
        logger.info("Starting Items Producer")
        self.es = AsyncElasticsearch(ES_HOST)
        await self.create_index()
        await self.load_state()

    async def stop(self) -> None:
        """Stops the processor."""
        logger.info("Stopping Items Producer")
        await self.es.close()

    async def create_index(self):
        """Ensure the jobs index exists in Elasticsearch."""
        exists = await self.es.indices.exists(index=INDEX_NAME)
        if not exists:
            mapping = {
                "mappings": {
                    "properties": {
                        "title": {"type": "text"},
                        "description": {"type": "text"},
                        "price": {"type": "double"},
                        "created_at": {"type": "date"},
                        "outbox_sent": {"type": "boolean"}
                    }
                }
            }
            await self.es.indices.create(index=INDEX_NAME, body=mapping)
            logger.info(f"Index '{INDEX_NAME}' created.")
        else:
            logger.info(f"Index '{INDEX_NAME}' already exists.")

    async def index_job(self, job_id: str) -> str:
        """Ingest a single job document into Elasticsearch."""
        job = {
            "title": f"Job {random.randint(1000, 9999)}",
            "description": f"Description for job {job_id}.",
            "price": random.randint(1, 100),
            "created_at": datetime.utcnow().isoformat(),
            "outbox_sent": False
        }
        await self.es.index(index=INDEX_NAME, id=job_id, body=job)
        logger.info(f"Ingested job {job_id}")
        return job_id

    async def generate_items(self, count: int) -> list[str]:
        """Ingest random job documents into Elasticsearch."""
        
        jobs = []
        
        for _ in range(count):
            jobs.append(str(uuid.uuid4()))

        tasks = [self.index_job(jobs[i]) for i in range(count)]
        await asyncio.gather(*tasks)
        
        self.last_update = datetime.now()
        self.items_produced += count
        await self.save_state()
        return jobs
    
    async def save_state(self) -> None:
        """Persists the current state to a file asynchronously."""
        state = {
            "items_produced": self.items_produced,
            "last_update": self.last_update.isoformat() if self.last_update else None
        }
        try:
            async with aiofiles.open(STATE_PATH, "w") as f:
                await f.write(json.dumps(state))
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    async def load_state(self) -> None:
        """Loads the saved state from a file asynchronously if it exists."""
        if os.path.exists(STATE_PATH):
            try:
                async with aiofiles.open(STATE_PATH, "r") as f:
                    content = await f.read()
                    state = json.loads(content)
                    self.items_produced = state.get("items_produced", 0)
                    self.last_update = (
                        datetime.fromisoformat(state["last_update"])
                        if state["last_update"] else None
                    )
                    logger.info(f"State loaded asynchronously: {state}")
            except Exception as e:
                logger.error(f"Failed to load state: {e}")
        else:
            logger.info("No previous state found, starting fresh.")
    
    async def info(self) -> dict[str, Any]:
        return {
            "items_produced": self.items_produced,
            "last_update": self.last_update,
        }