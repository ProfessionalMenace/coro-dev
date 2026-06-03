# start error logging
import tracemalloc

tracemalloc.start()

from config import TOKEN
from bot import Corobot

if __name__ == "__main__":
	bot = Corobot(command_prefix="!")
	bot.run(TOKEN)
