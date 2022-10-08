import trio
from dbconnection import DBConnection
from tcpcommunication import TCPCommunication
from custom_objects import Device
import pickle
import yaml


class BackupAppBackend:
    def __init__(self):
        self.db_con = DBConnection("storage.db")
        self.server_port = 12345
        self.config = yaml.safe_load(open("config.yml"))
        self.server_host = self.config["host_address"]
        # receive 4096 bytes each time
        self.buffer_size = 4096
        self.cmd_len = 128
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
                except Exception as e:
                    print("ehm no connection...")
                    print(e)
                finally:
                    self.tasks.remove(task)

    async def push_items(self):
        for dev in self.devices:
            stream = await trio.open_tcp_stream(dev.addr, self.server_port)
            with open("store_items", "rb") as file:
                async with stream:
                    cmd = "push items".zfill(self.cmd_len // 2)
                    await stream.send_all(cmd.encode())
                    # iterate over lambda? until reaching b""
                    for chunk in iter(lambda: file.read(self.buffer_size), b""):
                        await stream.send_all(chunk)

    async def get_marks(self):
        for dev in self.devices:
            stream = await trio.open_tcp_stream(dev.addr, self.server_port)
            async with stream:
                cmd = "get marks".zfill(self.cmd_len // 2)
                await stream.send_all(cmd.encode())

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
        new_connection = TCPCommunication(self.db_con, self.config)
        await new_connection.listen()

    async def run(self):
        async with trio.open_nursery() as nursery:
            self.nursery = nursery

            nursery.start_soon(self.server)
            nursery.start_soon(self.communication)


if __name__ == '__main__':
    trio.run(BackupAppBackend().run)
