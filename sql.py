'''

Utility file for manipulating and accessing the database

'''

import typing
import sqlite3

class Database:

	def __init__ (self, path: str):
		self.path = path
		self.connection = sqlite3.connect(self.path)
		self.cursor = self.connection.cursor()
		self.cursor.execute('''CREATE TABLE IF NOT EXISTS macros(
											id INT PRIMARY_KEY,
											name VARCHAR(20),
											author_id INT,
											code LONGTEXT
		)''')
		self.cursor.execute('''CREATE TABLE IF NOT EXISTS confessions(
											id INT PRIMARY_KEY
											author_id INT,
											message_id INT
		)''')