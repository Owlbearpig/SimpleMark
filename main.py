from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label


def get_users():
    with open("users", "r") as users_file:
        users = []
        for user in users_file.readlines():
            new_user = User(*user.split("__"))
            users.append(new_user)

    return users


class User:
    def __init__(self, username, full_name, id):
        self.username = username
        self.full_name = full_name
        self.id = int(id)

    def __str__(self):
        return self.username

    def __repr__(self):
        return self.__str__()


def get_items():
    with open("store_items", "r") as items_file:
        items = []
        for item in items_file.readlines():
            new_item = Item(*item.split("__"))
            items.append(new_item)

    return items


class Item:
    def __init__(self, name, price, category):
        self.name = name
        self.price = float(price)
        self.category = category

    def __repr__(self):
        return self.name + f"\n{self.price:.2f} €"


class NewUserLayout(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cols = 1

        self.inside = GridLayout()
        self.inside.cols = 2

        self.inside.add_widget(Label(text="First Name: ", font_size=40))
        self.name = TextInput(multiline=False, font_size=55)
        self.inside.add_widget(self.name)

        self.inside.add_widget(Label(text="Last Name: ", font_size=40))
        self.lastName = TextInput(multiline=False, font_size=55)
        self.inside.add_widget(self.lastName)

        self.add_widget(self.inside)
        self.submit = Button(text="Submit", font_size=40)
        self.add_widget(self.submit)

        self.back = Button(text="Go back", font_size=40)
        self.add_widget(self.back)


class StoreLayout(GridLayout):
    def __init__(self, **kwargs):
        super(StoreLayout, self).__init__(**kwargs)


class MyMainApp(App):
    def item_category_screen(self):
        category_screen = Screen(name="categories")
        self.items = get_items()
        self.categories = list(set([item.category for item in self.items]))

        layout = BoxLayout(orientation="horizontal")
        for category in self.categories:
            btn = Button(text=category, font_size=55)
            btn.bind(on_press=self.on_button_press)
            layout.add_widget(btn)
        category_screen.add_widget(layout)

        return category_screen

    def make_store_screen(self, category):
        def change_amount(instance):
            cur_amount = int(amount_text_field.text)
            if instance.text == "+":
                cur_amount += 1 * (cur_amount < 100)
            elif instance.text == "-":
                cur_amount -= 1 * (cur_amount > 1)
            amount_text_field.text = str(cur_amount)

        sel_items = [item for item in self.items if item.category == category]

        h_len = 5
        items_grid = []
        for i in range(len(sel_items) // h_len + 1 * ((len(sel_items) % h_len) != 0)):
            items_grid.append(sel_items[i * h_len:(i + 1) * h_len])

        v_layout = BoxLayout(orientation="vertical")
        increment_button = Button(text="+", font_size=55, halign='center')
        decrement_button = Button(text="-", font_size=55, halign='center')
        increment_button.bind(on_press=change_amount)
        decrement_button.bind(on_press=change_amount)
        amount_text_field = TextInput(multiline=False, readonly=True, font_size=110, text="1", halign='center')

        first_line = BoxLayout()
        first_line.add_widget(increment_button)
        first_line.add_widget(amount_text_field)
        first_line.add_widget(decrement_button)
        v_layout.add_widget(first_line)
        for row in items_grid:
            h_layout = BoxLayout()
            for item in row:
                item_button = Button(text=str(item), halign='center')
                item_button.bind(on_press=self.on_button_press)
                h_layout.add_widget(item_button)
            v_layout.add_widget(h_layout)

        return v_layout


    def update_users_screen(self):
        self.users = get_users()

        h_len = 5
        users_grid = []
        for i in range(len(self.users) // h_len + 1 * ((len(self.users) % h_len) != 0)):
            users_grid.append(self.users[i * h_len:(i + 1) * h_len])

        v_layout = BoxLayout(orientation="vertical")
        add_user_button = Button(text="Add user")
        add_user_button.bind(on_press=self.on_button_press)

        v_layout.add_widget(add_user_button)
        for row in users_grid:
            h_layout = BoxLayout()
            for user in row:
                user_button = Button(text=str(user))
                user_button.bind(on_press=self.on_button_press)
                user_button.ids['user_id'] = user.id
                h_layout.add_widget(user_button)
            v_layout.add_widget(h_layout)

        self.users_screen.add_widget(v_layout)

    def on_create_user(self):
        name, surname = self.new_user_layout.name.text, self.new_user_layout.lastName.text

        if name and surname:
            with open("users", "a") as users_file:
                id = max([user.id for user in self.users]) + 1
                users_file.write("\n" + f"{name[0].upper()}{surname[0].upper()}__{name}_{surname}__{id:05}")

        self.users_screen.clear_widgets()
        self.update_users_screen()

    def on_button_press(self, instance):
        def goto_main():
            self.sm.transition.direction = "right"
            self.sm.current = "users"

        def goto_items(category):
            self.sm.transition.direction = "up"
            self.sm.current = f"{category}_store_screen"

        def goto_categories():
            self.sm.transition.direction = "up"
            self.sm.current = "categories"

        button_text = instance.text
        if button_text == "Add user":
            self.sm.transition.direction = 'left'
            self.sm.current = "new_user"
        elif button_text == "Submit":
            self.on_create_user()
            goto_main()
        elif button_text == "Go back":
            goto_main()
        elif button_text in [user.username for user in self.users]:
            goto_categories()
        elif button_text in self.categories:
            goto_items(button_text)

    def build(self):
        self.sm = ScreenManager()

        # main/initial screen, select user or add user
        self.users_screen = Screen(name="users")
        self.update_users_screen()
        self.sm.add_widget(self.users_screen)

        # add user screen
        new_user_screen = Screen(name="new_user")
        self.new_user_layout = NewUserLayout()
        self.new_user_layout.submit.bind(on_press=self.on_button_press)
        new_user_screen.add_widget(self.new_user_layout)
        self.sm.add_widget(new_user_screen)

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
    MyMainApp().run()
