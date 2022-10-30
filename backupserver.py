from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.textinput import TextInput
import trio
from backupserver_backend import BackupAppBackend


class BackupAppGUI(App, BackupAppBackend):
    def __init__(self, **kwargs):
        super(BackupAppGUI, self).__init__(**kwargs)

    def build(self):
        self.sm = ScreenManager()

        # main screen
        self.main_screen = Screen(name="main")
        self.make_main_screen()
        self.sm.add_widget(self.main_screen)

        # confirmation screen
        self.confirmation_screen = Screen(name="confirmation_screen")
        self.sm.add_widget(self.confirmation_screen)

        return self.sm

    def setup_confirmation_screen(self):
        self.confirmation_screen.clear_widgets()

        v_layout = BoxLayout(orientation="vertical")

        self.status_field = TextInput(text="Type CONFIRM to remove all marks from remotes",
                                      readonly=False, multiline=True, font_size=28,
                                      halign="center", allow_copy=False)
        v_layout.add_widget(self.status_field)

        enter_btn = Button(text="Enter")
        enter_btn.bind(on_press=self.on_button_press)
        v_layout.add_widget(enter_btn)

        go_back_btn = Button(text="Go back")
        go_back_btn.bind(on_press=self.on_button_press)
        v_layout.add_widget(go_back_btn)

        self.confirmation_screen.add_widget(v_layout)

    def check_input(self):
        if self.status_field.text == "CONFIRM":
            self.tasks.append("reset marks")
            self.status_field.text = "Reset marks command sent"
        else:
            self.status_field.text = "Type CONFIRM to remove all marks from remotes"

    def on_button_press(self, instance):
        button_text = instance.text

        if button_text == "Go back":
            self.sm.transition.direction = "left"
            self.sm.current = "main"
        elif button_text == "Reset marks":
            self.setup_confirmation_screen()
            self.sm.transition.direction = "right"
            self.sm.current = "confirmation_screen"
        elif button_text == "Enter":
            self.check_input()
        else:
            self.tasks.append(button_text.lower())

    def make_main_screen(self):
        v_layout = BoxLayout(orientation="vertical")

        upd_items_btn = Button(text="Push items")
        upd_items_btn.bind(on_press=self.on_button_press)
        v_layout.add_widget(upd_items_btn)

        get_marks_btn = Button(text="Request tables")
        get_marks_btn.bind(on_press=self.on_button_press)
        v_layout.add_widget(get_marks_btn)

        reset_marks_btn = Button(text="Reset marks")
        reset_marks_btn.bind(on_press=self.on_button_press)
        v_layout.add_widget(reset_marks_btn)

        self.main_screen.add_widget(v_layout)

    async def app_func(self):
        async with trio.open_nursery() as nursery:
            self.nursery = nursery

            async def run_wrapper():
                # trio needs to be set so that it'll be used for the event loop
                await self.async_run(async_lib="trio")
                print("App done")
                nursery.cancel_scope.cancel()

            nursery.start_soon(run_wrapper)
            nursery.start_soon(self.tcp_comm.listen)
            nursery.start_soon(self.server)


if __name__ == '__main__':
    trio.run(BackupAppGUI().app_func)

