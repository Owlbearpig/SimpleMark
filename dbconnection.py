from pathlib import Path
import sqlite3


class DBConnection:
    def __init__(self, db=Path("Appdata") / "database.db"):
        self.con = sqlite3.connect(db)
        self.cur = self.con.cursor()
        self.table_cols = {"marks": ("time", "qty", "name", "price", "item_id", "user_id", "was_deleted"),
                           "items": ("name", "price", "category", "item_id"),
                           "users": ("username", "user_id"),
                           }

    def insert_into(self, table, values, cols, multi_insert=False):
        parameters = ", ".join(["?"] * len(cols))

        sql = f"INSERT INTO {table} {cols} VALUES ({parameters})"

        if multi_insert:
            self.cur.executemany(sql, values)
        else:
            self.cur.execute(sql, values)

        self.con.commit()

    def select_from(self, table):
        self.cur.execute(f"SELECT * FROM {table}")
        result = self.cur.fetchall()

        return result

    def truncate_table(self, table):
        # deletes content of table...
        self.cur.execute(f"DELETE FROM {table}")
        self.con.commit()

    def create_table(self, table, cols):
        try:
            self.cur.execute(f"CREATE TABLE {table}{cols}")
        except sqlite3.OperationalError as e:
            print(e)

    def update_record(self, table, new_values, cols, id_val, commit_now=True):
        if isinstance(cols, tuple):
            parameters = ", ".join(["?"] * len(cols))
        else:
            parameters = "?"
        id_expr = ""
        if table == "marks":
            id_expr = f"time = '{id_val}'"

        sql = f"UPDATE {table} SET {cols} = {parameters} WHERE {id_expr}"

        self.cur.execute(sql, new_values)
        if commit_now:
            self.con.commit()

    def update_table(self, table, values, cols, commit_now=True):
        id_expr = ""
        if table == "marks":
            id_expr = f"time = '{values[0]}'"
        if table == "users":
            id_expr = f"user_id = '{values[1]}'"
        parameters = ", ".join(["?"] * len(cols))
        sql = f"INSERT INTO {table} {cols} SELECT {parameters} " \
              f"WHERE NOT EXISTS (SELECT 1 FROM {table} WHERE {id_expr})"

        self.cur.execute(sql, values)
        if commit_now:
            self.con.commit()
