import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Suppress logs from 3rd party libraries
logging.getLogger("elasticsearch").setLevel(logging.WARNING)
logging.getLogger("elasticsearch.trace").setLevel(logging.CRITICAL)
logging.getLogger("elastic_transport").setLevel(logging.WARNING)
logging.getLogger("elastic_transport.transport").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
logging.getLogger("aio_pika").setLevel(logging.WARNING)
logging.getLogger("pika").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logging.getLogger("elasticsearch.trace").propagate = False
logging.getLogger("elastic_transport").propagate = False
logging.getLogger("elastic_transport.transport").propagate = False

logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn").setLevel(logging.WARNING)
