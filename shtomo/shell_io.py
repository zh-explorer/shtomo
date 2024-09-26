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
        # redirect stderr to stdout
        self.dup_stderr()

    def dup_stderr(self):
        self.execute_cmd(b"exec 2>&1")

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
        junk = self.recv(timeout=0.1)
        return data[:-len(token_end)]

    def download_file(self,src_file:string, dest_file: string):
        cmd_template = "cat %s"
        cmd = cmd_template % src_file
        cmd_return: bytes = self.run_cmd(cmd.encode("latin"))
        with open(dest_file, 'wb') as fp:
            fp.write(cmd_return)

    def upload_file(self, src_file: string, dest_file: string, encode: string):
        cmd_template3 = 'python -c "import sys;sys.stdout.buffer.write(sys.stdin.buffer.read(%d))" > %s'
        cmd_template2 = 'python -c "import sys;sys.stdout.write(sys.stdin.read(%d))" > %s'
        if not os.path.exists(src_file):
            print(f"target file {src_file} not exist")
            return
        with open(src_file, 'rb') as fp:
            data = fp.read()

        # get python version
        cmd_return: bytes = self.run_cmd(b"python --version")
        if cmd_return.startswith(b"Python 3"):
            cmd_template = cmd_template3
        elif cmd_return.startswith(b"Python 2"):
            cmd_template = cmd_template2
        else:
            try:
                print("Unknown python version %s" % (cmd_return.decode(encode)))
            except UnicodeDecodeError:
                print("Unknown python version %s" % cmd_return)
            return

        shell_cmd = cmd_template % (len(data), dest_file)
        shell_cmd = shell_cmd.encode(encode)

        self.execute_cmd(shell_cmd)
        time.sleep(1)  # wait for some times
        self.send(data)

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
        self.io_buffer = data + self.io_buffer

    def recv(self, size: int = 0, timeout=None) -> bytes:
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
                    if timeout is not None and int(time.time()) - start_time > timeout:
                        # timeout give up amd return data we read
                        break
        return data

    def recv_until(self, end: bytes):
        data = b''
        while end not in data:
            data += self.recv()
        idx = data.index(end)
        self.unget(data[idx + len(end):])
        data = data[:idx + len(end)]
        return data

    def set_term_mode(self, on: bool):
        self.term_mode = on
