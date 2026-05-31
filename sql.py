'''

Utility file for manipulating and accessing the database

'''

import typing
import sqlite3
from collections.abc import Iterable
import json

type QueryReturn = typing.Union[typing.Generator[sqlite3.Row], typing.Optional[sqlite3.Row]]
class MacroData(typing.TypedDict):
	name: str
	author_id: typing.ReadOnly[int]
	code: str
	query: bool

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
		if len(parameters) > 1 and parameters[0] is not None: self.cursor.executemany(query, parameters)
		else: self.cursor.execute(query, parameters)

	@typing.overload
	def query (self, /, query: str, parameters: typing.Any = None, size: typing.Literal[1] = 1) -> typing.Optional[sqlite3.Row]: ... # pyright: ignore[reportOverlappingOverload]

	@typing.overload
	def query (self, /, query: str, parameters: typing.Any = None, size: typing.Optional[int] = -1) -> typing.Generator[sqlite3.Row]: ...

	def query (self, /, query: str, parameters: typing.Any = None, size: typing.Optional[int] = -1) -> QueryReturn:
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


class MacroManager:
	def __init__ (self, path: str, database: Database):
		self.path = path
		self.database = database
		with open(self.path, "r") as macros:
			self.macros = json.load(macros)
	
	def save (self):
		'''update the json file'''
		print("Saving Macros")
		with open(self.path, "w") as macros:
			json.dump(self.macros, macros, indent=2)
	
	def create_macro (self, /, name: str, author_id: int, code: str):
		'''create a new macro'''
		if name in self.macros:
			raise ValueError(f"Macro {name} already exists")
		code = code.strip()
		print(code)
		self.macros[name] = {
			"name": name,
			"author_id": author_id,
			"code": code,
			"query": code.index("SELECT") == 0
		}
		self.save()
	
	def get_macros (self) -> typing.Generator[MacroData]:
		for name in self.macros:
			yield self.macros[name]
	
	def execute_macro (self, /, name: str, size: typing.Optional[int] = None, parameters: typing.Optional[typing.Dict[str, typing.Any]] = None) -> typing.Optional[QueryReturn]:
		'''
		Execute a Macro

		size should only be included if macro is a query
		
		'''
		if name not in self.macros:
			raise KeyError(f"Macro '{name}' not found")
		macro: MacroData = self.macros[name]
		if not macro["query"]:
			self.database.execute(parameters, query = macro["code"])
		else:
			return self.database.query(parameters=parameters, query=macro["code"], size=size)