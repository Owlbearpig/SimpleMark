import trio
from dbconnection import DBConnection
from tcpcommunication import TCPCommunication
from custom_objects import Device
import pickle
import yaml
from helpers import format_cmd


class BackupAppBackend:
    def __init__(self):
        self.config = yaml.safe_load(open("config.yml"))

        self.devices = [Device("192.168.52.6", "server", self.config),
                        Device("192.168.52.9", "dev1", self.config),
                        Device("192.168.52.10", "dev2", self.config)]

        self.server_port = self.config["server_port"]
        self.server_host = self.config["host_address"]
        self.buffer_size = self.config["buffer_size"]
        self.cmd_len = self.config["cmd_len"]

        self.db_con = DBConnection("storage.db")
        self.tcp_comm = TCPCommunication(self.db_con, self.devices)

        self.tasks = []

    async def server(self):
        while True:
            await trio.sleep(0.1)
            for dev in self.devices:
                if dev.is_host:
                    continue
                for task in self.tasks:
                    try:
                        await self.task_handler(dev, task)
                    except Exception as e:
                        print("ehm no connection...", e)
                    finally:
                        self.tasks.remove(task)

    async def task_handler(self, dev, task):
        if "push items" in task:
            await self.push_items(dev)
        elif "request tables" in task:
            await self.request_table(dev, "marks")
            await self.request_table(dev, "users")
            print("tables updated")

    async def push_items(self, dev):
        stream = await self.tcp_comm.open_stream(dev)
        if stream is None:
            return
        with open("store_items", "rb") as file:
            async with stream:
                cmd = format_cmd("push items")
                await stream.send_all(cmd)
                # iterate over lambda? until reaching b""
                for chunk in iter(lambda: file.read(self.buffer_size), b""):
                    await stream.send_all(chunk)
        print(f"pushed items to {dev}")

    async def request_table(self, dev, table):
        stream = await self.tcp_comm.open_stream(dev)
        if stream is None:
            return
        cmd = format_cmd(f"send {table}")
        await stream.send_all(cmd)

        await self.tcp_comm.stream_handler(stream, dev)
        # TODO Logging

    async def run(self):
        async with trio.open_nursery() as nursery:
            self.nursery = nursery

            nursery.start_soon(self.server)
            nursery.start_soon(self.tcp_comm.listen)


if __name__ == '__main__':
    trio.run(BackupAppBackend().run)
