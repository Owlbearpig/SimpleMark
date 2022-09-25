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
        for i, user in enumerate(users_file.readlines()):
            new_user = User(*user.split("__"))
            users.append(new_user)

    return users


class Item:
    def __init__(self, name, price):
        pass

class User:
    def __init__(self, username, full_name, id):
        self.username = username
        self.full_name = full_name
        self.id = int(id)

    def __str__(self):
        return self.username

    def __repr__(self):
        return self.__str__()


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

class MyMainApp(App):

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
        def goto_items():
            self.sm.transition.direction = "up"
            self.sm.current = "items"

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
            goto_items()


    def build(self):
        self.sm = ScreenManager()

        # main/initial screen, select user or add user
        self.users_screen = Screen(name="users")
        self.update_users_screen()

        # add user screen
        new_user_screen = Screen(name="new_user")
        self.new_user_layout = NewUserLayout()
        self.new_user_layout.submit.bind(on_press=self.on_button_press)
        new_user_screen.add_widget(self.new_user_layout)

        # available items screen
        items_screen = Screen(name="items")
        items_screen.add_widget(Button(text="abekat"))

        self.sm.add_widget(self.users_screen)
        self.sm.add_widget(new_user_screen)
        self.sm.add_widget(items_screen)

        return self.sm


if __name__ == "__main__":
    MyMainApp().run()
