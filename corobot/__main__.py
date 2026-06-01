#start error logging
import tracemalloc
tracemalloc.start()

from config import TOKEN # pyright: ignore[reportAttributeAccessIssue]
from bot import bot


if __name__ == "__main__":
	bot.run(TOKEN)
