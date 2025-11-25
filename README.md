# shtomo

shtomo 是一个用于管理和交互反向shell（reverse shell）和绑定shell（bind shell）的工具。它提供了两种工作模式：普通模式和终端模式，以及一系列内置命令来方便地管理远程shell会话。

## 功能特性

- 支持连接反向shell和监听绑定shell
- 提供两种交互模式：普通模式和完整终端模式
- 内置文件上传下载功能
- 支持通过SOCKS5代理连接
- 提供内置命令系统，方便执行常用操作
- 支持自定义编码设置

## 安装

### 从 pyproject.toml 安装

使用 pip 安装：

```bash
pip install .
```

或者使用 pdm 安装：

```bash
pdm install
```

### 依赖要求

- Python 3.8 或更高版本
- cmd2 ~= 2.4.3
- pysocks
- setuptools ~= 59.6.0

## 基本使用

### 连接反向shell

当你已经获得一个反向shell连接时，使用以下命令连接：

```bash
python main.py <目标IP> <端口>
```

例如：

```bash
python main.py 192.168.1.100 4444
```

### 监听绑定shell

如果你需要监听一个端口等待shell连接（绑定shell），使用 `-l` 或 `--listen` 参数：

```bash
python main.py -l <监听IP> <端口>
```

例如：

```bash
python main.py -l 0.0.0.0 4444
```

### 使用SOCKS5代理

如果需要通过SOCKS5代理连接，可以使用 `--socks5url` 参数：

```bash
python main.py --socks5url <代理URL> <目标IP> <端口>
```

例如：

```bash
python main.py --socks5url socks5://user:pass@127.0.0.1:1080 192.168.1.100 4444
```

## 工作模式

shtomo 提供两种工作模式，可以在它们之间自由切换。

### 普通模式

普通模式是默认的工作模式。在此模式下：

- 你可以直接输入命令，命令会被发送到远程shell执行
- 远程shell的输出会直接显示在你的终端
- 按 `Ctrl+C` 可以中断当前操作并进入内置命令模式

### 终端模式（Term Mode）

终端模式提供完整的终端功能，包括：

- 完整的终端交互体验
- 支持交互式程序（如 vim、nano 等）
- 支持命令历史记录
- 支持终端控制序列

#### 如何进入终端模式

1. 在普通模式下，按 `Ctrl+C` 进入内置命令模式
2. 你会看到提示符 `$> `，这表示你已经进入内置命令模式
3. 输入 `term` 命令并按回车
4. 系统会在远程shell中执行 `python -c 'import pty; pty.spawn("/bin/bash")'` 来启动一个伪终端
5. 自动切换到终端模式

#### 如何退出终端模式

在终端模式下，按 `Ctrl+D` 即可退出终端模式，返回到普通模式。

注意：退出终端模式不会断开shell连接，只是切换回普通模式。如果需要完全退出程序，请使用 `quit` 或 `exit` 命令。

## 内置命令

在普通模式下按 `Ctrl+C` 可以进入内置命令模式。内置命令模式提供了以下命令：

### term

进入终端模式，提供完整的终端交互功能。

```
$> term
```

### download

从远程shell下载文件到本地。

```
$> download <远程文件路径> <本地保存路径>
```

示例：

```
$> download /etc/passwd ./passwd_backup.txt
```

### upload

将本地文件上传到远程shell。

```
$> upload <本地文件路径> <远程保存路径>
```

示例：

```
$> upload ./exploit.py /tmp/exploit.py
```

### rcmd

在远程shell中执行命令并显示输出。这个命令会等待命令执行完成并返回结果。

```
$> rcmd <命令>
```

示例：

```
$> rcmd ls -la
$> rcmd whoami
$> rcmd cat /etc/passwd
```

### encode

设置终端编码。默认编码为 utf8。

```
$> encode <编码名称>
```

示例：

```
$> encode utf8
$> encode gbk
$> encode latin1
```

### return

从内置命令模式返回到普通模式，继续正常的shell交互。

```
$> return
```

### quit 或 exit

退出 shtomo 程序，断开与远程shell的连接。

```
$> quit
```

或

```
$> exit
```

## 在Python项目中使用

shtomo 可以作为Python库导入到你的项目中使用。

### 基本导入

```python
from shtomo import ShellUtil, ShellClient
```

### 连接shell示例

```python
from shtomo import ShellClient

# 创建客户端实例
client = ShellClient("192.168.1.100", 4444)

# 连接到远程shell
shell = client.connect_shell()

# 进入交互模式
shell.interactive()
```

### 监听shell示例

```python
from shtomo import ShellClient

# 创建客户端实例
client = ShellClient("0.0.0.0", 4444)

# 开始监听
client.listen_shell()

# 等待连接
shell = client.wait_shell()

# 进入交互模式
shell.interactive()
```

### 使用ShellUtil类

如果你已经有一个socket连接，可以直接使用 `ShellUtil` 类：

```python
import socket
from shtomo import ShellUtil

# 创建socket连接
sock = socket.socket()
sock.connect(("192.168.1.100", 4444))

# 创建ShellUtil实例
shell = ShellUtil(sock)

# 进入交互模式
shell.interactive()
```

### 执行命令并获取结果

```python
from shtomo import ShellClient

client = ShellClient("192.168.1.100", 4444)
shell = client.connect_shell()

# 执行命令并获取输出（字节形式）
output = shell.run_cmd(b"ls -la")
print(output.decode("utf-8"))

# 执行命令（不等待返回）
shell.execute_cmd(b"echo hello")
```

### 文件操作

```python
from shtomo import ShellClient

client = ShellClient("192.168.1.100", 4444)
shell = client.connect_shell()

# 下载文件
shell.download_file("/etc/passwd", "./passwd_backup.txt")

# 上传文件
shell.upload_file("./local_file.txt", "/tmp/remote_file.txt", "utf8")
```

### 使用SOCKS5代理

```python
import socks
import socket
from shtomo import ShellClient, SOCKSProxyManager

# 配置SOCKS5代理
proxy_url = "socks5://user:pass@127.0.0.1:1080"
s5option = SOCKSProxyManager(proxy_url).socks_options
socks.set_default_proxy(
    s5option["socks_version"],
    s5option["proxy_host"],
    s5option["proxy_port"],
    s5option["rdns"],
    s5option["username"],
    s5option["password"]
)
socket.socket = socks.socksocket

# 正常使用客户端
client = ShellClient("192.168.1.100", 4444)
shell = client.connect_shell()
shell.interactive()
```

## 使用技巧

1. **快速切换模式**：在普通模式下按 `Ctrl+C` 进入内置命令模式，使用 `term` 进入终端模式，在终端模式下按 `Ctrl+D` 返回普通模式。

2. **文件传输**：使用 `download` 和 `upload` 命令可以方便地在本地和远程之间传输文件，无需额外的工具。

3. **编码问题**：如果遇到中文乱码问题，可以使用 `encode` 命令切换编码，常见的有 utf8、gbk、latin1 等。

4. **命令执行**：在普通模式下直接输入命令即可执行，使用 `rcmd` 命令可以确保命令执行完成并获取完整输出。

5. **交互式程序**：如果需要运行 vim、nano 等交互式程序，必须先进入终端模式（使用 `term` 命令）。

## 注意事项

1. 退出终端模式（按 `Ctrl+D`）不会断开shell连接，只是切换回普通模式。要完全退出程序，请使用 `quit` 或 `exit` 命令。

2. 在终端模式下，某些控制字符的行为可能与普通模式不同。

3. 文件上传功能依赖于远程系统是否安装了Python，并且需要Python 2或Python 3。

4. 使用SOCKS5代理时，确保代理服务器正常运行且可访问。

5. 在某些网络环境下，可能需要调整超时设置或使用代理来建立连接。

## 许可证

WTFPL (Do What The F*ck You Want To Public License)

## 作者

explorer (hsadkhk@gmail.com)

## 项目地址

https://github.com/zh-explorer/shtomo
