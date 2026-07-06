import re
from corobot.sql import Database, MacroManager

def parameters_helper(sql: str):
	"""Detect parameters automatically"""
	parameters = {}
	for match in re.finditer(r":([A-Z]{4})", sql):
		parameters[match.group(1)] = input(f"Parameter {match.group(1)} > ")
	
	if parameters:
		return parameters
	else:
		return None

# SIMPLE SQL REPL
if __name__ == "__main__":
	print("Direct Access Enabled")
	confessions = Database("data/confessions.db")
	confessions_macro_manager = MacroManager("data/sql_macros.json")

	while True:
		try:
			# READ
			cmd, *args = input("> ").strip().split()
			
			# QUIT REPL
			if cmd == "QUIT":
				break
			
			# CREATE NEW MACRO
			elif cmd == "create_macro":
				name, *code = args 
				confessions_macro_manager.create_macro(
					name = name,
					code = " ".join(code),
					author_id = 0
				)
			
			# VIEW EXISTING MACROS
			elif cmd == "view_macro":
				if len(args) == 0:
					for macro in confessions_macro_manager.get_macros():
						print(macro)
				else:
					print(confessions_macro_manager.get_macro(args[0]))

			# RUN EXISTING MACRO 
			elif cmd == "use_macro":
				macro = confessions_macro_manager.get_macro(args[0])
				sql = macro["code"]

				if not macro["parameters"]:
					parameters = None	
				elif len(args) == 1:
					parameters = parameters_helper(sql) 
				elif len(macro["parameters"]) == len(args) - 1:
					parameters = dict(zip(macro["parameters"], args[1:]))
				else:
					print("Mismatched number of arguments!")
					continue

				ret = confessions.query(
					query = sql,
					size = -1,
					parameters = parameters
				)

				for row in ret:
					print(dict(row))
				
			# QUERY SQL DIRECTLY (use sql keyword LIMIT)
			elif cmd == "query":
				sql = input("instructions > ").strip()
				parameters = parameters_helper(sql) 
				ret = confessions.query(
					query = sql,
					size = -1,
					parameters = parameters
				)

				for row in ret:
					print(dict(row))

			else:
				print("Command not found!")
				
		except Exception as e:
			print(e)