import tracemalloc
import logging.config

from corobot.config import TOKEN
from corobot.bot import run_bot 

if __name__ == "__main__":
	logging.config.fileConfig('config/logging.conf', disable_existing_loggers=False)
	tracemalloc.start()
	run_bot(TOKEN)
