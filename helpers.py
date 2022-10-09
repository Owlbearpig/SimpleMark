import yaml

config = yaml.safe_load(open("config.yml"))


def format_cmd(cmd_s):
    cmd_s = str(cmd_s).lower()
    cmd = f"{cmd_s}".zfill(config["cmd_len"])
    return cmd.encode()


def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))
