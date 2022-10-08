from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
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

        return self.sm

    def on_button_press(self, instance):
        button_text = instance.text
        self.tasks.append(button_text)

    def make_main_screen(self):
        v_layout = BoxLayout(orientation="vertical")

        upd_items_btn = Button(text="Push items")
        upd_items_btn.bind(on_press=self.on_button_press)
        v_layout.add_widget(upd_items_btn)

        get_marks_btn = Button(text="Get marks")
        get_marks_btn.bind(on_press=self.on_button_press)
        v_layout.add_widget(get_marks_btn)

        self.main_screen.add_widget(v_layout)

    async def app_func(self):
        async with trio.open_nursery() as nursery:
            self.nursery = nursery

            async def run_wrapper():
                # trio needs to be set so that it'll be used for the event loop
                await self.async_run(async_lib='trio')
                print('App done')
                nursery.cancel_scope.cancel()

            nursery.start_soon(run_wrapper)
            nursery.start_soon(self.server)
            nursery.start_soon(self.communication)


if __name__ == '__main__':
    trio.run(BackupAppGUI().app_func)

