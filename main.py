from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.app import App
from kivy.uix.checkbox import CheckBox
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.core.window import Window
from datetime import datetime
from dbconnection import DBConnection
from tcpcommunication import TCPCommunication
from pathlib import Path
from custom_objects import User, Item, Device
import trio
import yaml


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


class HiMark(App):
    def __init__(self, **kwargs):
        super(HiMark, self).__init__(**kwargs)
        self.tcp_config = yaml.safe_load(open("config.yml"))

        self.devices = [Device("192.168.52.6", "backup", self.tcp_config),
                        Device("192.168.52.9", "dev1", self.tcp_config),
                        Device("192.168.52.10", "dev2", self.tcp_config)]

        self.selected_user = None
        self.qty_fields = {}
        # text to be displayed on users screen
        self.current_status = ""
        self.db_con = DBConnection()
        self.tcp_comm = TCPCommunication(self.db_con, self.devices)
        self.tcp_queue = []

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
            item = list(item)
            item[-1] = item[-1].replace("\r", "")

            new_item = Item(*item)
            items.append(new_item)

        return items

    def item_category_screen(self):
        category_screen = Screen(name="categories")
        self.items = self.get_items()
        self.categories = list(set([item.category for item in self.items]))

        h_layout = BoxLayout(orientation="vertical")
        layout = BoxLayout(orientation="horizontal")
        for category in self.categories:
            btn = Button(text=category, font_size=55)
            btn.bind(on_press=self.on_button_press)
            layout.add_widget(btn)
        h_layout.add_widget(layout)

        btn = Button(text="Purchase history", font_size=55)
        btn.bind(on_press=self.on_button_press)
        h_layout.add_widget(btn)

        go_back_btn = Button(text="Go back", font_size=55)
        go_back_btn.bind(on_press=self.on_button_press)
        h_layout.add_widget(go_back_btn)
        category_screen.add_widget(h_layout)

        return category_screen

    def update_store_screen(self):
        self.items = self.get_items()

        for store_screen in self.store_screens:
            store_screen.clear_widgets()
            category = store_screen.name.split("_")[0]
            store_layout = self.make_store_screen(category)
            store_screen.add_widget(store_layout)

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

        increment_button = Button(text="+", font_size=110, halign="center")
        decrement_button = Button(text="-", font_size=110, halign="center")
        increment_button.bind(on_press=change_amount)
        decrement_button.bind(on_press=change_amount)
        qty_field = TextInput(multiline=False, readonly=True, font_size=80, text="1", halign="center")
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

    def purchase_history_screen_layout(self):
        marks_table = self.db_con.select_from("marks")
        marks = [{a:b for a, b in zip(self.db_con.table_cols["marks"], mark_tuple)} for mark_tuple in marks_table]
        cur_user_marks = [mark for mark in marks if mark["user_id"] == self.selected_user.user_id]
        layout = GridLayout(cols=1, spacing=10, size_hint_y=None)
        layout.bind(minimum_height=layout.setter("height"))

        for mark in cur_user_marks:
            if mark["was_deleted"]:
                continue

            mark_vals = [str(val) for val in mark.values()]
            line = GridLayout(cols=2, spacing=1, size_hint_y=None)
            mark_text = Label(text=" ".join(mark_vals), height=40, size_hint_y=None)
            line.add_widget(mark_text)

            remove_mark_btn = Button(text="Remove", height=40, size_hint_y=None, size_hint_x=None)
            remove_mark_btn.bind(on_press=self.on_button_press)
            remove_mark_btn.ids["time"] = mark["time"]

            line.add_widget(remove_mark_btn)

            layout.add_widget(line)

        sv = ScrollView(size_hint=(1, None), size=(Window.width, Window.height))
        sv.add_widget(layout)

        # TODO add back button, integrate with sync. Sync flag?
        return sv

    def on_create_user(self):
        username = self.new_user_layout.username_input.text

        if username:
            user_id = str(max([int(user.user_id) for user in self.users]) + 1)
            self.db_con.insert_into("users", (username, user_id.zfill(5)), self.db_con.table_cols["users"])

        self.users_screen.clear_widgets()
        self.update_users_screen()

        for dev in self.devices:
            if dev.is_host:
                continue
            else:
                dev.synced_users = False

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

        row3 = GridLayout()
        row3.cols = 2
        self.ip_addr_field = TextInput(multiline=False, readonly=False, font_size=40, text="1", halign="left")
        self.ip_addr_field.text = self.tcp_config["host_address"]
        row3.add_widget(self.ip_addr_field)
        update_ip_btn = Button(text="Update address")
        update_ip_btn.bind(on_press=self.on_button_press)
        row3.add_widget(update_ip_btn)

        v_layout.add_widget(row3)

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

                vals = (now, qty, item.name, price, item_id, user_id, "0")
                cols = self.db_con.table_cols["marks"]
                self.db_con.insert_into("marks", vals, cols)

                self.status_field.text = f"Added {qty}x {item.name} to\n {user.username}"

                entry = "__".join([now, qty, item.name, price, item_id, user_id])
                break

        with open(f"Appdata/Marks/{int(user_id)}", "a") as file:
            file.write(entry + "\n")

        for dev in self.devices:
            if dev.is_host:
                continue
            else:
                dev.synced_marks = False

    def remove_mark(self, instance):
        mark_time = instance.ids["time"]
        self.db_con.update_record("marks", "1", "was_deleted", mark_time)
        self.on_purchase_history()

    def on_category_select(self):
        if self.tcp_comm.received_items:
            self.tcp_comm.received_items = False
            self.update_store_screen()

    def on_purchase_history(self):
        self.purchase_history_screen.clear_widgets()
        layout = self.purchase_history_screen_layout()
        self.purchase_history_screen.add_widget(layout)

    def on_button_press(self, instance):
        def goto_main():
            if self.tcp_comm.received_users:
                self.users_screen.clear_widgets()
                self.update_users_screen()
                self.tcp_comm.received_users = False

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

        def goto_purchase_history():
            self.sm.transition.direction = "down"
            self.sm.current = "purchase_history"

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
            self.on_category_select()
            goto_items(button_text)
        elif button_text == "Purchase history":
            self.on_purchase_history()
            goto_purchase_history()
        elif any([item.name in button_text for item in self.items]):
            self.buy_item(self.selected_user, instance.ids["item_id"])
            goto_main()
        elif button_text == "update items":
            self.tcp_queue.append("update_items")
        elif button_text == "Update address":
            self.tcp_config["host_address"] = self.ip_addr_field.text
            yaml.dump(self.tcp_config, open("config.yml", "w"))
        elif "time" in instance.ids.keys():
            self.remove_mark(instance)

    def build(self):
        self.check_dir()

        self.sm = ScreenManager()

        # setup main/initial screen, select user or add user
        self.users_screen = Screen(name="users")
        self.update_users_screen()
        self.sm.add_widget(self.users_screen)

        # setup add user screen
        new_user_screen = Screen(name="new_user")
        self.new_user_layout = NewUserLayout()
        self.new_user_layout.back.bind(on_press=self.on_button_press)
        self.new_user_layout.submit.bind(on_press=self.on_button_press)
        new_user_screen.add_widget(self.new_user_layout)
        self.sm.add_widget(new_user_screen)

        # purchase history screen
        self.purchase_history_screen = Screen(name="purchase_history")
        self.sm.add_widget(self.purchase_history_screen)

        # setup settings screen
        settings_screen = self.settings_screen()
        self.sm.add_widget(settings_screen)

        # setup categories
        category_screen = self.item_category_screen()
        self.sm.add_widget(category_screen)

        # setup available items screen; one for each category
        self.store_screens = []
        for category in self.categories:
            store_screen = Screen(name=f"{category}_store_screen")
            self.store_screens.append(store_screen)

        for store_screen in self.store_screens:
            self.sm.add_widget(store_screen)

        self.update_store_screen()

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
            nursery.start_soon(self.sync_loop)
            nursery.start_soon(self.tcp_comm.listen)

    async def sync_loop(self):
        sync_interval = 30
        while True:
            await trio.sleep(sync_interval)
            for dev in self.devices:
                if dev.is_host:
                    continue
                await self.sync_dev(dev, sync_interval)

    async def sync_dev(self, dev, interval):
        if dev.timeout:
            dev.timeout -= interval
            return
        stream = None
        if not dev.synced_marks:
            ret = await self.tcp_comm.send_table(stream, "marks", dev)
            dev.synced_marks = not bool(ret)
        if not dev.synced_users:
            ret = await self.tcp_comm.send_table(stream, "users", dev)
            dev.synced_users = not bool(ret)

        if (not dev.synced_users) or (not dev.synced_marks):
            dev.timeout = interval * 2 ** dev.timeouts
            dev.timeouts += 1
        else:
            dev.timeouts = 0


if __name__ == '__main__':
    trio.run(HiMark().app_func)
