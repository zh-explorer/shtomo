import selectors
import fcntl
import os
import logging
import socket
import time
import traceback
import random
import string
import cmd2
import argparse


class VShell(cmd2.Cmd):
    intro = "We are in internal shell util, run some prebuild function"
    prompt = "$> "

    def __init__(self, shell, completekey='tab', stdin=None, stdout=None):
        super().__init__(completekey, stdin, stdout, allow_cli_args=False)
        self.stop = False
        self.shell: ShellUtil = shell
        self.encode = "utf8"

    def do_return(self, arg):
        return True

    def do_quit(self, arg):
        self.stop = True
        return True

    def do_exit(self, arg):
        self.stop = True
        return True

    upload_parser = cmd2.Cmd2ArgumentParser()
    upload_parser.add_argument("src", help="src file path", completer=cmd2.Cmd.path_complete)
    upload_parser.add_argument("dest", help="dest file path")
    cmd_template3 = 'python -c "import sys;sys.stdout.buffer.write(sys.stdin.buffer.read(%d))" > %s'
    cmd_template2 = 'python -c "import sys;sys.stdout.write(sys.stdin.read(%d))" > %s'

    @cmd2.with_argparser(upload_parser)
    def do_upload(self, arg):
        src_file = arg.src
        if not os.path.exists(src_file):
            print(f"target file {src_file} not exist")
        with open(src_file, 'rb') as fp:
            data = fp.read()

        dest_file = arg.dest

        # get python version
        cmd_return: bytes = self.shell.run_cmd(b"python --version")
        if cmd_return.startswith(b"Python 3"):
            cmd_template = self.cmd_template3
        elif cmd_return.startswith(b"Python 2"):
            cmd_template = self.cmd_template2
        else:
            try:
                print("Unknown python version %s" % (cmd_return.decode(self.encode)))
            except UnicodeDecodeError:
                print("Unknown python version %s" % cmd_return)
            return

        shell_cmd = cmd_template % (len(data), dest_file)
        shell_cmd = shell_cmd.encode(self.encode)

        self.shell.execute_cmd(shell_cmd)
        time.sleep(1)  # wait for some times
        self.shell.send(data)

    encode_parser = cmd2.Cmd2ArgumentParser()
    encode_parser.add_argument("encode", help="terminal encoder")

    @cmd2.with_argparser(encode_parser)
    def do_encode(self, arg):
        encode = arg.encode
        self.encode = encode

    def do_rcmd(self, arg: str):
        arg = arg.encode(self.encode)
        data = self.shell.run_cmd(arg)
        try:
            print(data.decode(self.encode))
        except UnicodeDecodeError:
            print(data)


class ShellUtil:
    def __init__(self, io: socket.socket):
        self.io = io
        self.io_buffer = b''
        self.io.setblocking(False)
        self.stdin = self.get_unblock_stdin()
        self.sel = selectors.DefaultSelector()

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
            try:
                self.dup_to_terminal()
            except KeyboardInterrupt as e:
                inter = True
            except Exception as e:
                # do not exit
                logging.error("we face a error")
                traceback.print_exc()
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
                        break
                    os.write(1, data)
                else:
                    data = os.read(0, 1024)
                    if data == b'':
                        break
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("ip", help="target ip")
    parser.add_argument("port")

    arg = parser.parse_args()
    s = socket.socket()
    s.connect((arg.ip, int(arg.port)))
    shell = ShellUtil(s)
    shell.interactive()

