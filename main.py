import argparse
import socket
from shtomo import ShellUtil

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("ip", help="target ip")
    parser.add_argument("port")

    arg = parser.parse_args()
    s = socket.socket()
    s.connect((arg.ip, int(arg.port)))
    shell = ShellUtil(s)
    shell.interactive()
