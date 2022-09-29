import sqlite3
from main import SQLStorage

new_sql = SQLStorage()



#cur.execute("CREATE TABLE users(username, user_id)") # only needs to be executed ones obviously
"""# create users table
cols = ("username", "user_id")
with open("users", "r") as file:
    for line in file.readlines():
        values = line.split("__")
        new_sql.insert_into("users", values, cols)
"""

new_sql.select_from()
