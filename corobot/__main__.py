#start error logging
import tracemalloc
tracemalloc.start()

from config import TOKEN
from bot import bot

if __name__ == "__main__":
	bot.run(TOKEN)
