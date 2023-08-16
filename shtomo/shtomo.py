import os
import time
import cmd2


class VShell(cmd2.Cmd):
    intro = "We are in internal shell util, run some prebuild function"
    prompt = "$> "

    def __init__(self, shell, completekey='tab', stdin=None, stdout=None):
        super().__init__(completekey, stdin, stdout, allow_cli_args=False)
        self.stop = False
        self.shell = shell
        self.encode = "utf8"

    def do_return(self, arg):
        self.stop = False
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

    term_parse = cmd2.Cmd2ArgumentParser()
    term_parse.add_argument("switch", choices=["on", "off"])

    @cmd2.with_argparser(term_parse)
    def do_term(self, arg):
        if arg.switch == "on":
            self.shell.set_term_mode(True)
            self.shell.execute_cmd(b"python -c 'import pty; pty.spawn(\"/bin/bash\")'")
        else:
            self.shell.set_term_mode(False)
