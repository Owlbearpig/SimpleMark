import trio
import pickle
import yaml


def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))


class TCPCommunication:
    def __init__(self, db_con, devices, port=12345):
        self.db_con = db_con
        self.devices = devices
        # self.host_addr = "192.168.178.29"
        # self.host_addr = "192.168.52.9"
        self.config = yaml.safe_load(open("config.yml"))
        self.host_addr = self.config["host_address"]
        self.port = port
        self.cmd_len = 64
        # receive 4096 bytes each time
        self.buffer_size = 4096

    async def listen(self):
        while True:
            await trio.sleep(0.5)
            listeners = (await trio.open_tcp_listeners(self.port, host=self.host_addr))
            for listener in listeners:
                async with listener:
                    socket_stream = await self.accept(listener)
                    if socket_stream is not None:
                        await self.stream_handler(socket_stream)

    async def accept(self, listener):
        stream = await listener.accept()
        addr, port = stream.socket.getpeername()

        print(f"Addr: {addr}:{port} connected")
        if addr not in [dev.addr for dev in self.devices]:
            await stream.aclose()
            return
        else:
            print(f"Accepted {addr}:{port}")
            return stream

    async def stream_handler(self, stream):
        try:
            cmd_bytes = await stream.receive_some(self.cmd_len)
            cmd = cmd_bytes.decode()
            print("cmd:", cmd.replace("0", ""))
        except UnicodeDecodeError as e:
            cmd = ""
            print(e)
            await stream.aclose()

        try:
            if "push items" in cmd:
                await self.update_items(stream)
            elif "get marks" in cmd:
                await self.send_table(stream, "marks")
            elif "receive marks" in cmd:
                await self.receive_table(stream, "marks")
            elif "receive users" in cmd:
                await self.receive_table(stream, "users")
        except trio.ClosedResourceError as e:
            print(e)

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

    async def receive_table(self, stream, table):
        async with stream:
            received_data = b""
            async for chunk in stream:
                received_data += chunk

            marks = pickle.loads(received_data)

        cols = self.db_con.table_cols[table]
        for mark in marks:
            self.db_con.update_table(table, mark, cols, commit_now=False)
        self.db_con.con.commit()

    async def sync_table(self, dev, table):
        try:
            print(f"sending {table} to {dev}")
            cmd = f"receive {table}".zfill(self.cmd_len // 2)
            stream = await trio.open_tcp_stream(dev.addr, self.port)
            await stream.send_all(cmd.encode())
            await self.send_table(stream, table)
            print(f"successfully synced {table} with {dev}")
            return 0
        except Exception as e:
            print(e)
            return 1

    async def send_table(self, stream, table):
        entries = self.db_con.select_from(table)
        async with stream:
            data = pickle.dumps(entries)
            for chunk in chunker(data, self.buffer_size):
                await stream.send_all(chunk)
