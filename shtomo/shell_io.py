import os
import selectors
import fcntl
import logging
import traceback
import string
import random
import socket
import tty
from shtomo.shtomo import VShell


class ShellUtil:
    def __init__(self, io: socket.socket):
        self.io = io
        self.io_buffer = b''
        self.io.setblocking(False)
        self.stdin = self.get_unblock_stdin()
        self.sel = selectors.DefaultSelector()
        self.term_mode = False

    def get_unblock_stdin(self):
        fd = os.dup(0)
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        stdin = os.fdopen(fd)
        return stdin

    def clean_sel(self):
        try:
            self.sel.unregister(self.io)
        except KeyError:
            pass
        try:
            self.sel.unregister(self.stdin)
        except KeyError:
            pass

    def interactive(self):
        inter = False
        while True:
            self.clean_sel()
            self.sel.register(self.io, selectors.EVENT_READ)
            self.sel.register(self.stdin, selectors.EVENT_READ)
            if self.term_mode:
                tty.setraw(self.stdin.fileno())
            try:
                inter = self.dup_to_terminal()
            except KeyboardInterrupt as e:
                inter = True
            except Exception as e:
                # do not exit
                logging.error("we face a error")
                traceback.print_exc()
            finally:
                if self.term_mode:
                    tty.setcbreak(self.stdin.fileno())
            if inter:
                inter = False
                if self.cmdline_module():
                    # exit
                    return

    def dup_to_terminal(self):
        while True:
            for key, mask in self.sel.select():
                if key.fileobj == self.io:
                    data = self.io.recv(1024)
                    if data == b'':
                        return False
                    os.write(1, data)
                else:
                    data = os.read(0, 1024)
                    if self.term_mode:
                        if data == b'\x07':
                            self.io.send(b"\x03")
                            return True
                        elif data == b"\x04":
                            print("No ctrl-D!!!")
                            continue
                    if data == b'':
                        return False
                    self.io.send(data)

    def cmdline_module(self):
        try:
            shell = VShell(self)
            shell.cmdloop()
        except Exception:
            traceback.print_exc()
            return False
        return shell.stop

    def random_str(self):
        p = string.ascii_letters + string.digits
        return ''.join(random.choices(p, k=20)).encode("latin")

    def run_cmd(self, cmd: bytes) -> bytes:
        token = self.random_str()
        cmd_template = b"%s;echo '%s'" % (cmd, token)
        self.execute_cmd(cmd_template)
        data = self.recv_until(token + b"\n")
        return data[:-len(token) - 1]

    def execute_cmd(self, cmd: bytes):
        self.sendline(cmd)

    def sendline(self, data: bytes):
        self.send(data + b'\n')

    def send(self, data: bytes):
        self.clean_sel()
        self.sel.register(self.io, selectors.EVENT_WRITE)
        data_len = len(data)
        send_len = 0
        while send_len < data_len:
            for key, mask in self.sel.select():
                assert key.fileobj == self.io
                x = self.io.send(data[send_len:])
                send_len += x

    def recv(self, size: int = 0) -> bytes:
        assert size >= 0
        self.clean_sel()
        self.sel.register(self.io, selectors.EVENT_READ)
        if size == 0:
            data = self.io_buffer
            self.io_buffer = b''
            for key, mask in self.sel.select():
                assert key.fileobj == self.io
                while True:
                    try:
                        re = self.io.recv(1024)
                    except BlockingIOError:
                        break
                    data += re
        else:
            if len(self.io_buffer) >= size:
                data = self.io_buffer[:size]
                self.io_buffer = self.io_buffer[size:]
            else:
                read_len = len(self.io_buffer)
                data = self.io_buffer
                self.io_buffer = b''
                while read_len < size:
                    for key, mask in self.sel.select():
                        assert key.fileobj == self.io
                        re = self.io.recv(size - read_len)
                        read_len += len(re)
                        data += re
        return data

    def recv_until(self, end: bytes):
        data = b''
        while end not in data:
            data += self.recv()
        idx = data.index(end)
        self.io_buffer = data[idx + len(data):]
        data = data[:idx + len(data)]
        return data

    def set_term_mode(self, on: bool):
        self.term_mode = on
