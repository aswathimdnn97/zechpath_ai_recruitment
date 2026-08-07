import logging
import os

# # create log folder
os.makedirs("log",exist_ok=True)

# logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s| %(levelname)s| %(message)s |%(name)s",
    handlers= [logging.StreamHandler(),
               logging.FileHandler("log/ai_system_log.txt")]
        
)
# logger object
logger=logging.getLogger(__name__)