'''

Utility file for manipulating and accessing the database

'''

import typing
import sqlite3
import json
from discord import Interaction # purely for type hints
import re

import util

type QueryReturn = typing.Union[typing.Generator[sqlite3.Row], typing.Optional[sqlite3.Row]]
type DiscordUserId = int
class MacroData(typing.TypedDict):
	name: str
	author_id: typing.ReadOnly[DiscordUserId]
	code: str
	query: bool
	parameters: typing.Optional[typing.Sequence[str]]

class Database:

	def __init__ (self, path: str):
		self.path = path
		self.connection = sqlite3.connect(self.path)
		self.cursor = self.connection.cursor()
		self.cursor.execute('''CREATE TABLE IF NOT EXISTS confessions (
											id INT PRIMARY_KEY,
											author_id INTEGER,
											message_id INTEGER
		);''') # I feel like i'm missing a key here but I can't remember what it is
	
	def save (self):
		self.connection.commit()
		self.connection.close()
		self.connection = sqlite3.connect(self.path)
		self.cursor = self.connection.cursor()
	
	def execute (self, *parameters: typing.Dict[str, typing.Any], query: str):
		if len(parameters) > 1 and parameters[0] is not None: self.cursor.executemany(query, parameters)
		else: self.cursor.execute(query, parameters)

	@typing.overload
	def query (self, /, query: str, parameters: typing.Optional[typing.Dict[str, typing.Any]] = None, size: typing.Literal[1] = 1) -> typing.Optional[sqlite3.Row]: ... # pyright: ignore[reportOverlappingOverload]

	@typing.overload
	def query (self, /, query: str, parameters: typing.Optional[typing.Dict[str, typing.Any]] = None, size: typing.Optional[int] = -1) -> typing.Generator[sqlite3.Row]: ...

	def query (self, /, query: str, parameters: typing.Optional[typing.Dict[str, typing.Any]] = None, size: typing.Optional[int] = -1) -> QueryReturn:
		'''
		Creates and returns the results of a query

		If size is -1 or > 1, return all the results as a generator object yielding Row objects

		If size is 1, return the result as a Row object
		'''
		if parameters: self.execute(parameters, query=query)
		else: self.execute(query=query)
		if size == 1: return self.cursor.fetchone()
		i = 0
		while size and (size == -1 or i < size):
			ret = self.cursor.fetchone()
			if ret is None:
				break
			yield ret

class MacroError (Exception):
	def __init__ (self, macro_name: str, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.macro_name = macro_name
	def __str__ (self) -> str:
		return f"Generic Macro Error with Macro `{self.macro_name}`"
	async def send_error_message (self, interaction: Interaction, **kwargs):
		await util.send_error_message(interaction, str(self), **kwargs)
class MacroNotFound (MacroError):
	def __str__ (self) -> str:
		return f"Macro `{self.macro_name}` not found"
class MacroInUse (MacroError):
	def __str__ (self) -> str:
		return f"Macro `{self.macro_name}` in use"
class InsufficientPermissions (MacroError):
	def __str__ (self) -> str:
		return f"Insufficient Permissions for Macro `{self.macro_name}`"

class MacroManager:
	def __init__ (self, path: str):
		self.path = path
		with open(self.path, "r") as macros:
			self.macros: typing.Dict[str, MacroData] = json.load(macros)
	
	def save (self):
		'''update the json file'''
		print("Saving Macros")
		with open(self.path, "w") as macros:
			json.dump(self.macros, macros, indent=2)
	
	def create_macro (self, /, name: str, author_id: DiscordUserId, code: str):
		'''create a new macro'''
		if name in self.macros:
			raise MacroInUse(name)
		code = code.strip()
		parameters = []
		for match in re.finditer(r":([A-Z]{4})", code):
			parameters.append(match.group(1))
		self.macros[name] = {
			"name": name,
			"author_id": author_id,
			"code": code,
			"query": code.index("SELECT") == 0,
			"parameters": parameters
		}
		self.save()
	
	def edit_macro (self, /, name: str, editor: DiscordUserId, new_name: typing.Optional[str], new_code: typing.Optional[str], bypass_checks: bool = False):
		if name not in self.macros:
			raise MacroNotFound(name)
		if new_name in self.macros:
			raise MacroInUse(new_name)
		if editor != self.macros[name]["author_id"] and not bypass_checks:
			raise InsufficientPermissions(name)
		self.macros[name]["name"] = new_name or self.macros[name]["name"]
		if new_code:
			new_code = new_code.strip()
			parameters = []
			for match in re.finditer(r":([A-Z]{4})", new_code):
				parameters.append(match.group(1))
			self.macros[name]["code"] = new_code
			self.macros[name]["query"] = new_code.index("SELECT") == 0
			self.macros[name]["parameters"] = parameters
		self.save()

	
	def get_macros (self) -> typing.Generator[MacroData]:
		for name in self.macros:
			yield self.macros[name]
	
	def get_macro (self, name) -> MacroData:
		if name not in self.macros:
			raise MacroNotFound(name)
		return self.macros[name]
	
if __name__ == "__main__":
	print("Direct Access Enabled")
	confessions = Database("data/confessions.db")
	confessions_macro_manager = MacroManager("data/sql_macros.json")
	while True:
		try:
			cmd = input("> ").strip()
			if cmd == "QUIT":
				break
			if cmd == "macro":
				cmd = input ("MACRO > ").strip()
				if cmd.startswith("create_macro"):
					_, name, *code = cmd.split(" ")
					confessions_macro_manager.create_macro(name = name, code = " ".join(code), author_id = 0)
				if cmd.startswith("view_macro"):
					parsed = cmd.split(" ")
					if len(parsed) == 1:
						for macro in confessions_macro_manager.get_macros():
							print(macro)
					else:
						print(confessions_macro_manager.get_macro(parsed[1]))
			if cmd == "sql":
				cmd = input ("SQL > ").strip()
				if cmd == "query":
					sql = input("instructions > ").strip()
					size = int(input("size > ").strip())
					parameters = {}
					has_params = False
					for match in re.finditer(r":([A-Z]{4})", sql):
						has_params = True
						parameters[match.group(1)] = input(f"Parameter {match.group(1)} > ")
					ret = confessions.query(query = sql, size = size, parameters=parameters if has_params else None)
					if size == 1:
						ret = [ret]
					for row in ret:
						print(row)
					
		except Exception as e:
			print(e)