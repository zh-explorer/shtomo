import logging

from shtomo.shell_io import ShellUtil
from shtomo.parser_socks5_url import SOCKSProxyManager
import socks
import argparse
import socket
import threading


class ShellClient:
    def __init__(self, addr: str, port: int):
        self.addr = addr
        self.port = port
        self.shell_fd = None
        self.accept_thread = None

    def connect_shell(self):
        s = socket.socket()
        s.connect((self.addr, self.port))
        print(f"connect shell to {self.addr}:{self.port} success")
        shell = ShellUtil(s)
        return shell

    def listen_shell(self):
        s = socket.socket()
        s.bind((self.addr, self.port))
        s.listen()
        print(f"start listen to {self.addr}:{self.port}, wait for shell")

        def accept_shell():
            fd, _addr = s.accept()
            print(f"get connection from {_addr[0]}:{_addr[1]}")
            s.close()
            self.shell_fd = fd

        t = threading.Thread(target=accept_shell)
        t.start()
        self.accept_thread = t

    def wait_shell(self):
        self.accept_thread.join()
        shell = ShellUtil(self.shell_fd)
        return shell


# def listen_shell(addr: str, port: int):
#     s = socket.socket()
#     s.bind((addr, port))
#     s.listen()
#     print(f"start listen to {addr}:{port}, wait for shell")
#     fp, _addr = s.accept()
#     print(f"get connection from {_addr[0]}:{_addr[1]}")
#     s.close()
#     shell = ShellUtil(fp)
#     shell.interactive()
#
#
# def connect_shell(addr: str, port: int):
#     s = socket.socket()
#     s.connect((addr, port))
#     print(f"connect shell to {addr}:{port} success")
#     shell = ShellUtil(s)
#     shell.interactive()


def main_start():
    parser = argparse.ArgumentParser(description="shtomo client for connect shell")
    parser.add_argument("-l", "--listen", help="set client to listen a shell", action="store_true")
    parser.add_argument("addr", help="target to connect or listen")
    parser.add_argument("port", help="port to connect or listen", type=int)
    parser.add_argument("--socks5url", help="socks5 proxy url")

    arg = parser.parse_args()
    socks5url = arg.socks5url
    if socks5url is not None:
        s5option = SOCKSProxyManager(socks5url).socks_options
        socks.set_default_proxy(s5option["socks_version"], s5option["proxy_host"], s5option["proxy_port"],
                                s5option["rdns"],
                                s5option["username"], s5option["password"])
        socket.socket = socks.socksocket

    c = ShellClient(arg.addr, arg.port)
    # listen mode
    if arg.listen:
        c.listen_shell()
        shell = c.wait_shell()
        shell.interactive()
    else:
        shell = c.connect_shell()
        shell.interactive()
