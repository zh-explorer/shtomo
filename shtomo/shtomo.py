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

    download_parser = cmd2.Cmd2ArgumentParser()
    download_parser.add_argument("src", help="remote src file path")
    download_parser.add_argument("dest", help="local dest file path", completer=cmd2.Cmd.path_complete)

    @cmd2.with_argparser(download_parser)
    def do_download(self, arg):
        src_file = arg.src
        dest_file = arg.dest
        return self.shell.download_file(src_file, dest_file)


    upload_parser = cmd2.Cmd2ArgumentParser()
    upload_parser.add_argument("src", help="local src file path", completer=cmd2.Cmd.path_complete)
    upload_parser.add_argument("dest", help="remote dest file path")

    @cmd2.with_argparser(upload_parser)
    def do_upload(self, arg):
        src_file = arg.src
        dest_file = arg.dest
        return self.shell.upload_file(src_file, dest_file, self.encode)

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

    def do_term(self, arg):
        self.shell.execute_cmd(b"python -c 'import pty; pty.spawn(\"/bin/bash\")'")
        self.shell.set_term_mode(True)
        return True

    def emptyline(self) -> bool:
        pass
