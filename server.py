import socket
import hashlib
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.app import App, async_runTouchApp
from kivy.uix.checkbox import CheckBox
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from datetime import datetime
import sqlite3
from pathlib import Path
import trio
from main import DBConnection
import pickle


class ServerApp(App):
    def __init__(self, **kwargs):
        super(ServerApp, self).__init__(**kwargs)
        self.db_con = DBConnection("storage.db")
        self.server_host = "192.168.178.29"
        self.server_port = 12345
        # receive 4096 bytes each time
        self.buffer_size = 4096
        self.cmd_len = 128
        SEPARATOR = "123"
        self.tasks = []

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

    async def server(self):
        while True:
            await trio.sleep(0.1)
            for task in self.tasks:
                try:
                    if "Push items" in task:
                        await self.push_items()
                    elif "Get marks" in task:
                        await self.get_marks()
                except OSError:
                    print("ehm no connection...")
                finally:
                    self.tasks.remove(task)
    async def push_items(self):
        stream = await trio.open_tcp_stream(self.server_host, self.server_port)
        with open("store_items", "rb") as file:
            async with stream:
                cmd = "push items".zfill(self.cmd_len // 2)
                await stream.send_all(cmd.encode())
                # iterate over lambda? until reaching b""
                for chunk in iter(lambda: file.read(self.buffer_size), b""):
                    await stream.send_all(chunk)

    async def get_marks(self):
        stream = await trio.open_tcp_stream(self.server_host, self.server_port)
        async with stream:
            cmd = "get marks".zfill(self.cmd_len // 2)
            await stream.send_all(cmd.encode())

            received_data = b""
            async for chunk in stream:
                received_data += chunk

            marks = pickle.loads(received_data)

        cols = ("time", "qty", "name", "price", "item_id", "user_id")
        self.db_con.insert_into("marks", marks, cols, multi_insert=True)
        # TODO Logging


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


if __name__ == '__main__':
    trio.run(ServerApp().app_func)

"""
def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()
"""
