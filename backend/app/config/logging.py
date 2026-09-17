import logging
import sys

def setup_logging() -> None:
    """Configures system-wide logging formats and levels."""
    log_format = (
        "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] - %(message)s"
    )
    
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set levels for noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
