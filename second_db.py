import sqlite3

con = sqlite3.connect("appdata.db")

cur = con.cursor()

#cur.execute("CREATE TABLE users(username, user_id)")

res = cur.execute("SELECT username FROM users")

print(res.fetchone())
