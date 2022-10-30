import yaml


class Device:
    def __init__(self, name, addr):
        self.name = name
        self.addr = addr
        self.config = yaml.safe_load(open("config.yml"))
        self.is_host = (addr == self.config["tcp_config"]["host_address"])
        self.timeout = 0
        self.timeouts = 0

    def __str__(self):
        return f"{self.addr}, {self.name}"

    def reset_timeout(self):
        self.timeout = 0
        self.timeouts = 0


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
