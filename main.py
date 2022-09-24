from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput


class User:
    def __init__(self, username, full_name, user_id):
        self.username = username
        self.full_name = full_name
        self.user_id = user_id


class MainApp(App):
    def build(self):
        self.main_layout = BoxLayout(orientation="vertical")

        self.update_main()

        return self.main_layout

    def update_main(self):

        with open("users_data", "r") as users_file:
            users = []
            for i, user in enumerate(users_file.readlines()):
                new_user = User(*user.split("__"))
                users.append(new_user)

        buttons = [
            ["Add user"],
            ["7", "8", "9", "/"],
            ["4", "5", "6", "*"],
            ["1", "2", "3", "-"],
            [".", "0", "C", "+"],
        ]
        for row in buttons:
            h_layout = BoxLayout()
            for label in row:
                button = Button(text=label, pos_hint={"center_x": 0.5, "center_y": 0.5})
                button.bind(on_press=self.on_button_press)
                h_layout.add_widget(button)
            self.main_layout.add_widget(h_layout)

        return

    def on_button_press(self, instance):
        button_text = instance.text

        if button_text == "Add user":
            self.main_layout.clear_widgets()
            self.main_layout.add_widget(Button(text="asd", pos_hint={"center_x": 0.5, "center_y": 0.5}))


if __name__ == "__main__":
    app = MainApp()
    app.run()
