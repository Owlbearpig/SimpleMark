import trio
from dbconnection import DBConnection
from devtcpcommunication import DevTCPCommunication
from custom_objects import Device
import pickle
import yaml
from helpers import format_cmd


class BackupAppBackend:
    def __init__(self):
        self.app_config = yaml.safe_load(open("config.yml"))
        self.devices = [Device(name, addr) for name, addr in self.app_config["devices"].items()]

        self.server_port = self.app_config["tcp_config"]["server_port"]
        self.server_host = self.app_config["tcp_config"]["host_address"]
        self.buffer_size = self.app_config["tcp_config"]["buffer_size"]
        self.cmd_len = self.app_config["tcp_config"]["cmd_len"]

        self.db_con = DBConnection("storage.db")
        self.tcp_comm = DevTCPCommunication(self.db_con)

        self.tasks = []

    async def server(self):
        while True:
            await trio.sleep(0.1)
            for task in self.tasks:
                for dev in self.devices:
                    if dev.is_host:
                        continue
                    try:
                        await self.task_handler(dev, task)
                    except Exception as e:
                        print(f"No connection to {dev}", e)

                self.tasks.remove(task)

    async def task_handler(self, dev, task):
        if "push items" in task:
            await self.push_items(dev)
        elif "request tables" in task:
            await self.send_cmd(dev, "send users")
            await self.send_cmd(dev, "send marks")
            print("tables updated")
        elif "reset marks" in task:
            await self.send_cmd(dev, "reset marks")

    async def send_cmd(self, dev, cmd):
        stream = await self.tcp_comm.open_stream(dev)
        if stream is None:
            return
        f_cmd = format_cmd(cmd)
        await stream.send_all(f_cmd)
        if "reset marks" in cmd:
            await stream.aclose()

        await self.tcp_comm.stream_handler(stream, dev)

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

    async def run(self):
        async with trio.open_nursery() as nursery:
            self.nursery = nursery

            nursery.start_soon(self.server)
            nursery.start_soon(self.tcp_comm.listen)


if __name__ == '__main__':
    trio.run(BackupAppBackend().run)
