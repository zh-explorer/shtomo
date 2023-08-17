import logging

from shtomo.shell_io import ShellUtil
from shtomo.parser_socks5_url import SOCKSProxyManager
import socks
import argparse
import socket


def listen_shell(addr: str, port: int):
    s = socket.socket()
    s.bind((addr, port))
    s.listen()
    print(f"start listen to {addr}:{port}, wait for shell")
    fp, _addr = s.accept()
    print(f"get connection from {_addr[0]}:{_addr[1]}")
    s.close()
    shell = ShellUtil(fp)
    shell.interactive()


def connect_shell(addr: str, port: int):
    s = socket.socket()
    s.connect((addr, port))
    print(f"connect shell to {addr}:{port} success")
    shell = ShellUtil(s)
    shell.interactive()


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

    # listen mode
    if arg.listen:
        listen_shell(arg.addr, arg.port)
    else:
        connect_shell(arg.addr, arg.port)
