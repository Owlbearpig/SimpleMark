import sqlite3
from main import DBConnection
from pathlib import Path

new_sql = DBConnection("storage.db")

cur = new_sql.cur
#cur.execute("CREATE TABLE items(name, price, category, item_id)")  # only needs to be executed ones obviously
#cols = ("name", "price", "category", "item_id")
#cur.execute("CREATE TABLE users(username, user_id)")  # only needs to be executed ones obviously
#cols = ("username", "user_id")
#cur.execute("CREATE TABLE marks(time, qty, name, price, item_id, user_id)")  # only needs to be executed ones obviously
cols = ("username", "user_id")

"""# populate table
with open("users", "r") as file:
    for line in file.readlines():
        # split and remove line breaks
        values = [value.replace("\n", "") for value in line.split("__")]
        new_sql.insert_into("users", values, cols)
"""
#res = new_sql.select_from("users")
#print(res)


