from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.app import App
from kivy.uix.checkbox import CheckBox
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from datetime import datetime
import sqlite3
from pathlib import Path
import trio
import pickle


def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))


class Device:
    def __init__(self, addr, name):
        self.addr = addr
        self.name = name

    def __str__(self):
        return f"addr: {self.addr}, name: {self.name}"


class TCPConnection:
    def __init__(self, db_con, port=12345):
        self.db_con = db_con
        # self.host_addr = "192.168.178.29"
        # self.host_addr = "192.168.52.9"
        self.host_addr = "127.0.0.1"
        self.port = port
        self.addr_whitelist = ["127.0.0.1", "192.168.52.6", "192.168.52.9"]
        self.devices = [Device("192.168.52.9", "dev1"), ]
        self.cmd_len = 128
        # receive 4096 bytes each time
        self.buffer_size = 4096
        SEPARATOR = "123"

    async def listen(self):
        while True:
            await trio.sleep(0.5)
            listeners = (await trio.open_tcp_listeners(self.port, host=self.host_addr))
            for listener in listeners:
                async with listener:
                    socket_stream = await self.accept(listener)
                    if socket_stream is not None:
                        await self.stream_handler(socket_stream)

    async def accept(self, listener):
        stream = await listener.accept()
        addr, port = stream.socket.getpeername()

        print(f"Addr: {addr}:{port} connected")
        if addr not in self.addr_whitelist:
            await stream.aclose()
            return
        else:
            print(f"Accepted {addr}:{port}")
            return stream

    async def stream_handler(self, stream):
        cmd = (await stream.receive_some(self.cmd_len)).decode()
        print("cmd:", cmd.replace("0", ""))

        try:
            if "push items" in cmd:
                await self.update_items(stream)
            elif "get marks" in cmd:
                await self.send_table(stream, "marks")
            elif "syncing marks" in cmd:
                await self.receive_table(stream, "marks")
            elif "syncing users" in cmd:
                await self.receive_table(stream, "users")
        except trio.ClosedResourceError as e:
            print(e)

    async def update_items(self, stream):
        chunk_s = ""
        async for chunk in stream:
            chunk_s += chunk.decode()

        self.db_con.truncate_table("items")

        for line in chunk_s.split("\n"):
            cols = self.db_con.table_cols["items"]
            values = line.split("__")
            if len(values) == 4:
                self.db_con.insert_into("items", values, cols)

    async def receive_table(self, stream, table):
        async with stream:
            received_data = b""
            async for chunk in stream:
                received_data += chunk

            marks = pickle.loads(received_data)

        cols = self.db_con.table_cols[table]
        for mark in marks:
            self.db_con.update_table(table, mark, cols, commit_now=False)
        self.db_con.con.commit()

    async def sync_table(self, table):
        for dev in self.devices:
            print(f"syncing {table}, dev: {dev}")
            cmd = f"sync {table}".zfill(self.cmd_len // 2)
            stream = await trio.open_tcp_stream(dev.addr, self.port)
            await stream.send_all(cmd.encode())
            await self.send_table(stream, table)

    async def send_table(self, stream, table):
        entries = self.db_con.select_from(table)
        async with stream:
            data = pickle.dumps(entries)
            for chunk in chunker(data, self.buffer_size):
                await stream.send_all(chunk)


class DBConnection:
    def __init__(self, db=Path("Appdata") / "database.db"):
        self.con = sqlite3.connect(db)
        self.cur = self.con.cursor()
        self.table_cols = {"marks": ("time", "qty", "name", "price", "item_id", "user_id"),
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


class User:
    def __init__(self, username, user_id):
        self.username = username
        self.user_id = user_id

    def __str__(self):
        return f"{self.username}"

    def __repr__(self):
        return self.__str__()


class Item:
    def __init__(self, name, price, category, item_id):
        self.name = name
        self.price = price
        self.category = category
        self.item_id = item_id

    def __repr__(self):
        return self.name + f"\n{float(self.price):.2f} €"


class NewUserLayout(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cols = 1

        self.inside = GridLayout()
        self.inside.cols = 2

        self.inside.add_widget(Label(text="Username: ", font_size=40))
        self.username_input = TextInput(multiline=False, font_size=55)
        self.inside.add_widget(self.username_input)

        self.add_widget(self.inside)
        self.submit = Button(text="Submit", font_size=40)
        self.add_widget(self.submit)

        self.back = Button(text="Go back", font_size=40)
        self.add_widget(self.back)


class StoreLayout(GridLayout):
    def __init__(self, **kwargs):
        super(StoreLayout, self).__init__(**kwargs)


class HiMark(App):
    def __init__(self, **kwargs):
        super(HiMark, self).__init__(**kwargs)
        self.selected_user = None
        self.qty_fields = {}
        # text to be displayed on users screen
        self.current_status = ""
        self.db_con = DBConnection()
        self.tcp_queue = []
        self.unsynced_marks = False
        self.unsynced_users = False

    def check_dir(self):
        p = Path("Appdata") / "Marks"
        if not p.is_dir():
            p.mkdir(parents=True)

    def get_users(self):
        all_users = self.db_con.select_from("users")

        users = []
        for user in all_users:
            new_user = User(*user)
            users.append(new_user)
        users.sort(key=lambda x: x.username)

        return users

    def get_items(self):
        all_items = self.db_con.select_from("items")
        items = []
        for item in all_items:
            new_item = Item(*item)
            items.append(new_item)

        return items

    def item_category_screen(self):
        category_screen = Screen(name="categories")
        self.items = self.get_items()
        self.categories = list(set([item.category for item in self.items]))

        h_layout = BoxLayout(orientation="vertical")
        go_back_btn = Button(text="Go back", font_size=55)
        go_back_btn.bind(on_press=self.on_button_press)
        layout = BoxLayout(orientation="horizontal")
        for category in self.categories:
            btn = Button(text=category, font_size=55)
            btn.bind(on_press=self.on_button_press)
            layout.add_widget(btn)
        h_layout.add_widget(layout)
        h_layout.add_widget(go_back_btn)
        category_screen.add_widget(h_layout)

        return category_screen

    def make_store_screen(self, category):
        def change_amount(instance):
            cur_amount = int(qty_field.text)
            if instance.text == "+":
                cur_amount += 1 * (cur_amount < 100)
            elif instance.text == "-":
                cur_amount -= 1 * (cur_amount > 1)
            qty_field.text = str(cur_amount)

        sel_items = [item for item in self.items if item.category == category]

        h_len = 5
        items_grid = []
        for i in range(len(sel_items) // h_len + 1 * ((len(sel_items) % h_len) != 0)):
            items_grid.append(sel_items[i * h_len:(i + 1) * h_len])

        increment_button = Button(text="+", font_size=110, halign='center')
        decrement_button = Button(text="-", font_size=110, halign='center')
        increment_button.bind(on_press=change_amount)
        decrement_button.bind(on_press=change_amount)
        qty_field = TextInput(multiline=False, readonly=True, font_size=80, text="1", halign='center')
        qty_field.ids["category"] = category
        self.qty_fields[category] = qty_field

        first_line = BoxLayout()
        first_line.add_widget(increment_button)
        first_line.add_widget(qty_field)
        first_line.add_widget(decrement_button)
        v_layout = BoxLayout(orientation="vertical")
        v_layout.add_widget(first_line)
        for row in items_grid:
            h_layout = BoxLayout()
            for item in row:
                item_button = Button(text=str(item), halign='center', font_size=18)
                item_button.bind(on_press=self.on_button_press)
                item_button.ids["item_id"] = item.item_id
                h_layout.add_widget(item_button)
            v_layout.add_widget(h_layout)

        go_back_btn = Button(text="Go back", font_size=55)
        go_back_btn.bind(on_press=self.on_button_press)
        v_layout.add_widget(go_back_btn)

        return v_layout

    def update_users_screen(self):
        self.users = self.get_users()

        h_len = 5
        users_grid = []
        for i in range(len(self.users) // h_len + 1 * ((len(self.users) % h_len) != 0)):
            users_grid.append(self.users[i * h_len:(i + 1) * h_len])

        v_layout = BoxLayout(orientation="vertical")
        self.status_field = TextInput(text=self.current_status, readonly=False, multiline=True, font_size=28,
                                      halign="center", allow_copy=False)
        v_layout.add_widget(self.status_field)

        add_user_button = Button(text="Add user", font_size=55)
        add_user_button.bind(on_press=self.on_button_press)
        v_layout.add_widget(add_user_button)

        for row in users_grid:
            h_layout = BoxLayout()
            for user in row:
                user_button = Button(text=str(user))
                user_button.bind(on_press=self.on_button_press)
                user_button.ids['user_id'] = user.user_id
                h_layout.add_widget(user_button)
            v_layout.add_widget(h_layout)

        self.users_screen.add_widget(v_layout)

    def on_create_user(self):
        username = self.new_user_layout.username_input.text

        if username:
            user_id = str(max([user.user_id for user in self.users]) + 1)
            self.db_con.insert_into("users", (username, user_id.zfill(5)), self.db_con.table_cols["users"])

        self.users_screen.clear_widgets()
        self.update_users_screen()
        self.unsynced_users = True

    def settings_screen(self):
        settings_screen = Screen(name="settings")

        v_layout = BoxLayout(orientation="vertical")
        row1 = GridLayout()
        row1.cols = 2

        row1.add_widget(Label(text="En. add user"))
        self.en_add_user = CheckBox(active=True)
        row1.add_widget(self.en_add_user)
        v_layout.add_widget(row1)

        row2 = GridLayout()
        row2.cols = 2
        row2.add_widget(Label(text="update items"))
        update_items_btn = Button(text="update items")
        update_items_btn.bind(on_press=self.on_button_press)
        row2.add_widget(update_items_btn)
        v_layout.add_widget(row2)

        go_back_btn = Button(text="Go back", font_size=55)
        go_back_btn.bind(on_press=self.on_button_press)
        v_layout.add_widget(go_back_btn)

        settings_screen.add_widget(v_layout)

        return settings_screen

    def select_user(self, selected_user_id):
        for user in self.users:
            if user.user_id == selected_user_id:
                self.selected_user = user
                break

    def buy_item(self, user, item_id):
        user_id, item_id = str(user.user_id), str(item_id)
        entry = ""
        for item in self.items:
            if str(item.item_id) == item_id:
                now, price = str(datetime.now()), str(item.price)
                qty = self.qty_fields[item.category].text

                vals = (now, qty, item.name, price, item_id, user_id)
                cols = self.db_con.table_cols["marks"]
                self.db_con.insert_into("marks", vals, cols)

                self.status_field.text = f"Added {qty}x {item.name} to\n {user.username}"

                entry = "__".join([now, qty, item.name, price, item_id, user_id])
                break

        with open(f"Appdata/Marks/{int(user_id)}", "a") as file:
            file.write(entry + "\n")

        self.unsynced_marks = True

    def on_button_press(self, instance):
        def goto_main():
            self.sm.transition.direction = "right"
            self.sm.current = "users"
            self.selected_user = None
            for qty_field in self.qty_fields.values():
                qty_field.text = "1"

        def goto_items(category):
            self.sm.transition.direction = "up"
            self.sm.current = f"{category}_store_screen"

        def goto_categories():
            self.sm.transition.direction = "up"
            self.sm.current = "categories"

        button_text = instance.text
        if button_text == "Add user":
            if self.status_field.text == "1234":
                self.sm.transition.direction = "down"
                self.sm.current = "settings"
            elif self.en_add_user.active:
                self.sm.transition.direction = "left"
                self.sm.current = "new_user"

        elif button_text == "Submit":
            self.on_create_user()
            goto_main()
        elif button_text == "Go back":
            goto_main()
        elif button_text in [str(user) for user in self.users]:
            goto_categories()
            self.select_user(instance.ids["user_id"])
        elif button_text in self.categories:
            goto_items(button_text)
        elif any([item.name in button_text for item in self.items]):
            self.buy_item(self.selected_user, instance.ids["item_id"])
            goto_main()
        elif button_text == "update items":
            self.tcp_queue.append("update_items")

    def build(self):
        self.check_dir()

        self.sm = ScreenManager()

        # main/initial screen, select user or add user
        self.users_screen = Screen(name="users")
        self.update_users_screen()
        self.sm.add_widget(self.users_screen)

        # add user screen
        new_user_screen = Screen(name="new_user")
        self.new_user_layout = NewUserLayout()
        self.new_user_layout.back.bind(on_press=self.on_button_press)
        self.new_user_layout.submit.bind(on_press=self.on_button_press)
        new_user_screen.add_widget(self.new_user_layout)
        self.sm.add_widget(new_user_screen)

        # settings screen
        settings_screen = self.settings_screen()
        self.sm.add_widget(settings_screen)

        # categories
        category_screen = self.item_category_screen()
        self.sm.add_widget(category_screen)

        # available items screen
        for category in self.categories:
            store_screen = Screen(name=f"{category}_store_screen")
            store_layout = self.make_store_screen(category)
            store_screen.add_widget(store_layout)
            self.sm.add_widget(store_screen)

        return self.sm

    async def app_func(self):
        async with trio.open_nursery() as nursery:
            self.nursery = nursery

            async def run_wrapper():
                # trio needs to be set so that it'll be used for the event loop
                await self.async_run(async_lib='trio')
                print('App done')
                nursery.cancel_scope.cancel()

            nursery.start_soon(run_wrapper)
            nursery.start_soon(self.communication_server)
            nursery.start_soon(self.sync_loop)

    async def communication_server(self):
        new_connection = TCPConnection(self.db_con)
        await new_connection.listen()

    async def sync_loop(self):
        while True:
            await trio.sleep(10)
            try:
                if self.unsynced_marks or self.unsynced_users:
                    new_connection = TCPConnection(self.db_con)
                    if self.unsynced_marks:
                        await new_connection.sync_table("marks")
                        self.unsynced_marks = False
                    if self.unsynced_users:
                        await new_connection.sync_table("users")
                        self.unsynced_users = False
            except Exception as e:
                print(e)


if __name__ == '__main__':
    trio.run(HiMark().app_func)
