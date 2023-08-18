import os
import selectors
import fcntl
import logging
import time
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
        self.console = VShell(self)

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
                        # if data == b'\x07':
                        #     self.io.send(b"\x03")
                        #     return True

                        # if we find a ctrl+D int term mode.
                        # we just send ctrl+c to clean input and run exit to quit pty bash shell.
                        # shtomo will switch back to normal mode
                        # we don't want to lost out shell. use quit cmd to conform a quit
                        if data == b"\x04":
                            self.io.send(b"\x03")
                            time.sleep(0.5)
                            self.io.send(b"exit\n")
                            self.set_term_mode(False)
                            tty.setcbreak(self.stdin.fileno())
                            return True
                    if data == b'':
                        return False
                    self.io.send(data)

    def cmdline_module(self):
        try:
            self.console.cmdloop()
        except Exception:
            traceback.print_exc()
            return False
        return self.console.stop

    def random_str(self):
        p = string.ascii_letters + string.digits
        return ''.join(random.choices(p, k=20)).encode("latin")

    def run_cmd(self, cmd: bytes) -> bytes:
        token_start = self.random_str()
        token_end = self.random_str()
        cmd_template = b"echo '%s';%s;echo '%s'" % (token_start, cmd, token_end)
        self.execute_cmd(cmd_template)

        while True:
            data = self.recv_until(token_start)
            next_ch = self.recv(1)
            if next_ch != b"'":  # this is an echo back, skip it
                break

        if next_ch == b"\r":  # need eat a \n char
            next_ch = self.recv(1)
            if next_ch != b'\n':  # ??? single \r?
                self.unget(next_ch)
        elif next_ch != b"\n":  # ??? where is my new line?
            self.unget(next_ch)

        data = self.recv_until(token_end)
        junk = self.recv()
        return data[:-len(token_end)]

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

    # put data back to stream
    def unget(self, data: bytes):
        self.io_buffer += data

    def recv(self, size: int = 0, timeout=0) -> bytes:
        assert size >= 0
        self.clean_sel()
        self.sel.register(self.io, selectors.EVENT_READ)
        if size == 0:
            data = self.io_buffer
            self.io_buffer = b''
            for key, mask in self.sel.select(timeout=timeout):
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
                start_time = int(time.time())
                read_len = len(self.io_buffer)
                data = self.io_buffer
                self.io_buffer = b''
                while read_len < size:
                    for key, mask in self.sel.select(timeout=1):
                        assert key.fileobj == self.io
                        re = self.io.recv(size - read_len)
                        read_len += len(re)
                        data += re
                    if int(time.time()) - start_time > timeout:
                        # timeout give up amd return data we read
                        break
        return data

    def recv_until(self, end: bytes):
        data = b''
        while end not in data:
            data += self.recv()
        idx = data.index(end)
        self.io_buffer = data[idx + len(end):]
        data = data[:idx + len(end)]
        return data

    def set_term_mode(self, on: bool):
        self.term_mode = on
