import sqlite3
from main import DBConnection

new_sql = DBConnection()
#new_con = sqlite3.connect("appdata.db")

#cur = new_con.cursor()
#cur.execute("CREATE TABLE marks(time, qty, name, price, item_id, user_id)")  # only needs to be executed ones obviously
"""# create users table
cols = ("name", "price", "category", "item_id")
with open("store_items", "r") as file:
    for line in file.readlines():
        values = line.split("__")
        new_sql.insert_into("items", values, cols)

res = new_sql.select_from("items")
print(res)
"""

