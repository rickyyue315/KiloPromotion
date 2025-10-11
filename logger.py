import logging
import os

# Create logger
logger = logging.getLogger('promotion_app')
logger.setLevel(logging.ERROR)

# Create file handler
log_file = 'app.log'
if not os.path.exists(log_file):
    open(log_file, 'w').close()

file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.ERROR)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Add handler to logger
logger.addHandler(file_handler)