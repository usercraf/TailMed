import sqlite3


TOKEN = ''

base = sqlite3.connect('sport.db')
cur = base.cursor()