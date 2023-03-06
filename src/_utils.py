import logging
import os

logger = logging.getLogger(__name__)


def stop_processing() -> bool:
    """Return whether to stop job submission processing or not."""
    should_stop_processing = os.environ.get("HALT_PROCESSING", "0")
    if int(should_stop_processing) == 1:
        logger.info("HALT_PROCESSING is set, stopping Glue Job submission.")
        return True
    return False
