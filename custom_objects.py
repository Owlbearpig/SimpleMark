class Device:
    def __init__(self, addr, name, config):
        self.addr = addr
        self.name = name
        self.synced_marks = True
        self.synced_users = True
        self.is_host = addr == config["host_address"]
        self.connection_fails = 0

    def __str__(self):
        return f"addr: {self.addr}, name: {self.name}"


class User:
    def __init__(self, username, user_id):
        self.username = username
        self.user_id = user_id

    def __str__(self):
        return f"{self.username}"

    def __repr__(self):
        return self.__str__()


class Item:
    def __init__(self, name, price, category, item_id):
        self.name = name
        self.price = price
        self.category = category
        self.item_id = item_id

    def __repr__(self):
        return self.name + f"\n{float(self.price):.2f} €"
