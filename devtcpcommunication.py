import trio
import pickle
import yaml
from helpers import chunker, format_cmd
from custom_objects import Device
from imports import Logger


class DevTCPCommunication:
    def __init__(self, db_con, port=None):
        self.db_con = db_con
        self.app_config = yaml.safe_load(open("config.yml"))
        self.devices = [Device(name, addr) for name, addr in self.app_config["devices"].items()]
        self.host_addr = self.app_config["tcp_config"]["host_address"]
        if port is None:
            self.port = self.app_config["tcp_config"]["server_port"]
        self.cmd_len = self.app_config["tcp_config"]["cmd_len"]
        self.buffer_size = self.app_config["tcp_config"]["buffer_size"]
        self.received_items = False
        self.received_users = False

    async def open_stream(self, dev):
        Logger.debug(f"Connecting to {dev.addr} on port {self.port}...")
        try:
            stream = await trio.open_tcp_stream(dev.addr, self.port)
        except OSError:
            Logger.debug(f"Could not open tcp stream to {dev.addr} on port {self.port}")
            return None

        return stream

    async def listen(self):
        retries, timeout = 0, 0
        while True:
            await trio.sleep(1)
            try:
                await trio.sleep(timeout)
                listeners = (await trio.open_tcp_listeners(host=self.host_addr, port=self.port))
                Logger.debug(f"Listening on {self.host_addr};{self.port}")
                for listener in listeners:
                    async with listener:
                        socket_stream, dev = await self.accept(listener)
                        if socket_stream is not None:
                            await self.stream_handler(socket_stream, dev)
                retries, timeout = 0, 0
            except OSError as e:
                timeout += 30 * 2 ** retries
                retries += 1
                Logger.debug(repr(e))
                Logger.debug(f"Check IP settings.")
                Logger.debug(f"Waiting {timeout} seconds until resuming listening, {retries} failed attempts.")

    async def accept(self, listener):
        # check if connection is from known device then reset timeouts
        stream = await listener.accept()
        addr, port = stream.socket.getpeername()

        Logger.debug(f"{addr};{port} connected")
        connected_dev = None
        for dev in self.devices:
            if dev.addr == addr:
                connected_dev = dev
                dev.reset_timeout()
                break

        if connected_dev is not None:
            Logger.debug(f"Accepted {connected_dev}")
            return stream, connected_dev
        else:
            await stream.aclose()
            return None, None

    async def stream_handler(self, stream, dev):
        cmd_bytes = await stream.receive_some(self.cmd_len)
        if cmd_bytes == b"":
            return
        cmd = cmd_bytes.decode().replace("0", "")
        Logger.debug(f"Incoming cmd: {cmd}")

        try:
            if "push items" in cmd:
                await self.update_items(stream)
            elif "send marks" in cmd:
                await self.send_table(stream, "marks", dev)
            elif "send users" in cmd:
                await self.send_table(stream, "users", dev)
            elif "receive marks" in cmd:
                await self.receive_table(stream, "marks", dev)
            elif "receive users" in cmd:
                await self.receive_table(stream, "users", dev)
            elif "reset marks" in cmd:
                await self.reset_marks_table()
        except trio.ClosedResourceError:
            Logger.debug("Incoming stream closed, returning")

    async def reset_marks_table(self):
        Logger.debug("Truncating marks")
        self.db_con.truncate_table("marks")
        Logger.debug("Truncated marks")

    async def update_items(self, stream):
        chunk_s = ""
        async for chunk in stream:
            chunk_s += chunk.decode()

        self.db_con.truncate_table("items")

        for line in chunk_s.split("\n"):
            cols = self.db_con.table_cols["items"]
            values = line.split("__")
            if len(values) == 4:
                self.db_con.insert_into("items", values, cols)
        self.received_items = True
        Logger.debug("Received new items")

    async def receive_table(self, stream, table, dev):
        Logger.debug(f"Receiving {table} from {dev}")
        async with stream:
            received_data = b""
            async for chunk in stream:
                received_data += chunk

            table_data = pickle.loads(received_data)

        cols = self.db_con.table_cols[table]
        for row in table_data:
            # if row was deleted and table == marks then force update of the row in table with id == time
            if (table == "marks") and int(row[6]):  # was deleted flag
                self.db_con.update_record(table, row, cols, row[0], commit_now=False)
            self.db_con.update_table(table, row, cols, commit_now=False)
        self.db_con.con.commit()

        if table == "users":
            self.received_users = True

    async def send_table(self, stream, table, dev):
        try:
            if stream is None:
                stream = await self.open_stream(dev)
                if stream is None:
                    raise Exception(f"Could not open stream to {dev}")

            Logger.debug(f"Sending {table} to {dev}")
            cmd = format_cmd(f"receive {table}")
            await stream.send_all(cmd)

            entries = self.db_con.select_from(table)
            async with stream:
                data = pickle.dumps(entries)
                for chunk in chunker(data, self.buffer_size):
                    await stream.send_all(chunk)
            Logger.debug(f"Successfully sent {table} to {dev}")
            return 0
        except Exception as e:
            Logger.debug(repr(e))
            return 1
