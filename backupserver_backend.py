import trio
from dbconnection import DBConnection
from tcpcommunication import TCPCommunication
from custom_objects import Device
import pickle
import yaml
from helpers import format_cmd


class BackupAppBackend:
    def __init__(self):
        self.db_con = DBConnection("storage.db")
        self.config = yaml.safe_load(open("config.yml"))
        self.server_port = self.config["server_port"]
        self.server_host = self.config["host_address"]
        self.buffer_size = self.config["buffer_size"]
        self.cmd_len = self.config["cmd_len"]
        self.devices = [Device("192.168.52.6", "server", self.config),
                        Device("192.168.52.9", "dev1", self.config),
                        Device("192.168.52.10", "dev2", self.config)]
        self.tasks = []

    async def server(self):
        while True:
            await trio.sleep(0.1)
            for task in self.tasks:
                try:
                    if "Push items" in task:
                        await self.push_items()
                    elif "Get marks" in task:
                        await self.get_marks()
                    elif "sync users" in task:
                        await self.sync_users() # TODO trigger sync
                except Exception as e:
                    print("ehm no connection...")
                    print(e)
                finally:
                    self.tasks.remove(task)

    async def push_items(self):
        for dev in self.devices:
            if dev.is_host:
                continue
            stream = await trio.open_tcp_stream(dev.addr, self.server_port)
            with open("store_items", "rb") as file:
                async with stream:
                    cmd = format_cmd("push items")
                    await stream.send_all(cmd)
                    # iterate over lambda? until reaching b""
                    for chunk in iter(lambda: file.read(self.buffer_size), b""):
                        await stream.send_all(chunk)

    async def get_marks(self):
        for dev in self.devices:
            stream = await trio.open_tcp_stream(dev.addr, self.server_port)
            async with stream:
                cmd = format_cmd("get marks")
                await stream.send_all(cmd)

                received_data = b""
                async for chunk in stream:
                    received_data += chunk

                marks = pickle.loads(received_data)

            cols = self.db_con.table_cols["marks"]
            for mark in marks:
                self.db_con.update_table("marks", mark, cols, commit_now=False)
            self.db_con.con.commit()
            # TODO Logging

    async def communication(self):
        new_connection = TCPCommunication(self.db_con, self.devices)
        await new_connection.listen()

    async def run(self):
        async with trio.open_nursery() as nursery:
            self.nursery = nursery

            nursery.start_soon(self.server)
            nursery.start_soon(self.communication)


if __name__ == '__main__':
    trio.run(BackupAppBackend().run)
