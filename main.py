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


class DBConnection:
    def __init__(self):
        self.con = sqlite3.connect("appdata.db")
        self.cur = self.con.cursor()

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


class User:
    def __init__(self, username, user_id):
        self.username = username
        self.user_id = int(user_id)

    def __str__(self):
        return f"{self.username}"

    def __repr__(self):
        return self.__str__()


class Item:
    def __init__(self, name, price, category, item_id):
        self.name = name
        self.price = float(price)
        self.category = category
        self.item_id = item_id

    def __repr__(self):
        return self.name + f"\n{self.price:.2f} €"


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
        self.current_status = ""
        self.db_con = DBConnection()

    def check_dir(self):
        if not (Path("Appdata") / "Marks").is_dir():
            p = Path("temp/")
            p.mkdir(parents=True, exist_ok=True)


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
            self.db_con.insert_into("users", (username, user_id.zfill(5)), ("username", "user_id"))

        self.users_screen.clear_widgets()
        self.update_users_screen()

    def settings_screen(self):
        settings_screen = Screen(name="settings")

        v_layout = BoxLayout(orientation="vertical")
        row1 = GridLayout()
        row1.cols = 2

        row1.add_widget(Label(text='En. add user'))
        self.en_add_user = CheckBox(active=True)
        row1.add_widget(self.en_add_user)
        v_layout.add_widget(row1)

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
        user_id = user.user_id
        entry = ""
        for item in self.items:
            if item.item_id == item_id:
                now = datetime.now()
                qty = self.qty_fields[item.category].text

                vals = (now, qty, item.name, item.price, item_id, user_id)
                cols = ("time", "qty", "name", "price", "item_id", "user_id")
                self.db_con.insert_into("marks", vals, cols)

                self.status_field.text = f"Added {qty}x {item.name} to\n {user.username}"

                entry = "__".join([now, qty, item.name, item.price, item_id, user_id])
                break

        with open(f"Appdata/Marks/{user_id}", "a") as file:
            file.write(entry)

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

    def build(self):
        self.dir_check =

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


if __name__ == "__main__":
    HiMark().run()
