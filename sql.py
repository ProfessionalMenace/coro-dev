'''

Utility file for manipulating and accessing the database

'''

import typing
import sqlite3
from collections.abc import Iterable

class Database:

	def __init__ (self, path: str):
		self.path = path
		self.connection = sqlite3.connect(self.path)
		self.cursor = self.connection.cursor()
		self.cursor.execute('''CREATE TABLE IF NOT EXISTS macros (
											name TEXT PRIMARY_KEY,
											author_id INTEGER,
											code TEXT,
											query BOOLEAN
		);''')
		self.cursor.execute('''CREATE TABLE IF NOT EXISTS confessions (
											id INT PRIMARY_KEY
											author_id INTEGER,
											message_id INTEGER
		);''')
	
	def save (self):
		self.connection.commit()
		self.connection.close()
		self.connection = sqlite3.connect(self.path)
		self.cursor = self.connection.cursor()
	
	def execute (self, *parameters: typing.Any, query: str):
		if len(parameters) > 1: self.cursor.executemany(query, parameters)
		else: self.cursor.execute(query, parameters)

	@typing.overload
	def query (self, /, query: str, parameters: typing.Any = None, size: typing.Literal[1] = 1) -> typing.Optional[sqlite3.Row]: ... # pyright: ignore[reportOverlappingOverload]

	@typing.overload
	def query (self, /, query: str, parameters: typing.Any = None, size: int = -1) -> typing.Generator[sqlite3.Row]: ...

	def query (self, /, query: str, parameters: typing.Any = None, size: int = -1) -> typing.Union[typing.Generator[sqlite3.Row], typing.Optional[sqlite3.Row]]:
		'''
		Creates and returns the results of a query

		If size is -1 or > 1, return all the results as a generator object yielding Row objects

		If size is 1, return the result as a Row object
		'''
		if parameters: self.execute(parameters, query=query)
		else: self.execute(query=query)
		if size == 1: return self.cursor.fetchone()
		i = 0
		while size == -1 or i < size:
			ret = self.cursor.fetchone()
			if ret is None:
				break
			yield ret

	@typing.overload
	def use_macro (self, /, name: str, size: typing.Literal[1], parameters: typing.Any = ()) -> typing.Optional[sqlite3.Row]: ... # pyright: ignore[reportOverlappingOverload]

	@typing.overload
	def use_macro (self, /, name: str, size: int, parameters: typing.Any = ()) -> typing.Generator[sqlite3.Row]: ...

	def use_macro (self, /, name: str, size: int = -1, parameters: typing.Any = ()) -> typing.Optional[typing.Union[typing.Generator[sqlite3.Row], typing.Optional[sqlite3.Row]]]:
		macro = self.query(size = 1, parameters = (name,), query = '''
										 SELECT code, query
										 FROM macros
										 WHERE name == ?;
		''')
		if macro:
			if macro["query"]:
				return self.query(query = macro["code"], parameters=parameters, size=size)
			self.execute(parameters, query=macro["code"])
	
	def create_macro (self, /, name: str, author_id: int, code: str):
		code = code.strip()
		self.execute((name, author_id, code, code.index("SELECT") == 0), query='''
										 INSERT INTO macros(name, author_id, code, query)
							 			 VALUES (?, ?, ?, ?);
		''')


if __name__ == "__main__":
	print("direct access enabled")
	confessions = Database("config/confessions.db")
	while True:
		cmd = input("> ")
		if cmd == "QUIT":
			break
		if cmd.find("SELECT") == 0:
			size = int(input("Size: "))
			ret = confessions.query(query=cmd, size = size)
			if isinstance(ret, sqlite3.Row):
				print(ret)
			else:
				for row in ret:
					print(row)
