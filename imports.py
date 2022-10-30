import os
from os import getcwd
from pathlib import Path
from kivy.config import Config
Config.set("kivy", "log_dir", Path(getcwd()) / "logs")
Config.set("kivy", "log_maxfiles", 5)
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
from kivy.logger import Logger
