import logging
from logging.handlers import RotatingFileHandler
import paramiko
import threading
import socket
import time
from pathlib import Path

SSH_BANNER = "SSH-2.0-MySSHServer_1.0"

base_dir = Path(__file__).parent
server_key = base_dir / 'staticf' / 'server.key'
creds_audits_log_local_file_path = base_dir / 'log_files' / 'creds_audits.log'
cmd_audits_log_local_file_path = base_dir / 'log_files' / 'cmd_audits.log'

host_key = paramiko.RSAKey(filename=server_key)

logging_format = logging.Formatter('%(message)s')

# cmd_audits.log — every command typed during a session
funnel_logger = logging.getLogger('FunnelLogger')
funnel_logger.setLevel(logging.INFO)
funnel_handler = RotatingFileHandler(cmd_audits_log_local_file_path, maxBytes=1_000_000, backupCount=5)
funnel_handler.setFormatter(logging_format)
funnel_logger.addHandler(funnel_handler)

# creds_audits.log — every login attempt (IP, username, password)
creds_logger = logging.getLogger('CredsLogger')
creds_logger.setLevel(logging.INFO)
creds_handler = RotatingFileHandler(creds_audits_log_local_file_path, maxBytes=1_000_000, backupCount=5)
creds_handler.setFormatter(logging_format)
creds_logger.addHandler(creds_handler)


class Server(paramiko.ServerInterface):

    def __init__(self, client_ip, input_username=None, input_password=None):
        self.event = threading.Event()
        self.client_ip = client_ip
        self.input_username = input_username
        self.input_password = input_password

    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
    
    def get_allowed_auths(self, username):
        return "password"

    def check_auth_password(self, username, password):
        safe_username = username.replace('\n', '').replace('\r', '').replace(',', '')
        safe_password = password.replace('\n', '').replace('\r', '').replace(',', '')
        funnel_logger.info(f'Client {self.client_ip} attempted connection with username: {safe_username}, password: {safe_password}')
        creds_logger.info(f'{self.client_ip}, {safe_username}, {safe_password}')
        if self.input_username is not None and self.input_password is not None:
            if username == self.input_username and password == self.input_password:
                return paramiko.AUTH_SUCCESSFUL
            else:
                return paramiko.AUTH_FAILED
        else:
            return paramiko.AUTH_SUCCESSFUL
    
    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return True

    def check_channel_exec_request(self, channel, command):
        command = str(command)
        return True

def emulated_shell(channel, client_ip):
    channel.send(b"corporate-jumpbox2$ ")
    command = b""
    while True:
        char = channel.recv(1)
        channel.send(char)
        if not char:
            channel.close()
            return

        command += char
        if char == b"\r":
            cmd = command.strip().decode('utf-8', errors='replace')

            if cmd:
                funnel_logger.info(f"Command {cmd} executed by {client_ip}")

            if cmd == 'exit':
                channel.send(b"\r\nGoodbye!\r\n")
                channel.close()
                return

            elif cmd == 'pwd':
                response = b"\r\n/usr/local\r\n"

            elif cmd == 'whoami':
                response = b"\r\ncorpuser1\r\n"

            elif cmd == 'id':
                response = b"\r\nuid=1000(corpuser1) gid=1000(the_corpusers) groups=1000(the_corpusers),4(adm),24(cdrom),27(sudo),30(dip),46(plugdev),116(lpadmin),125(sambashare)\r\n"

            elif cmd == 'hostname' or cmd == 'cat /etc/hostname':
                response = b"\r\ncorporate-jumpbox2\r\n"

            elif cmd in ('ls', 'ls --color', 'ls --color=auto'):
                response = b"\r\njumpbox1.conf\tpasswd\trsa_id\r\n"

            elif cmd == 'ls -l':
                response = (
                    b"\r\ntotal 3\r\n"
                    b"-rw-r--r-- 1 corpuser1 thecorpusers  1234 Dec 22 12:34 jumpbox1.conf\r\n"
                    b"-rw-r--r-- 1 root      root           456 Dec 22 12:34 passwd\r\n"
                    b"-rw------- 1 corpuser1 thecorpusers  7890 Dec 22 12:34 rsa_id\r\n"
                )

            elif cmd in ('ls -la', 'ls -al'):
                response = (
                    b"\r\ntotal 16\r\n"
                    b"drwxr-xr-x 2 corpuser1 thecorpusers 4096 Dec 22 12:34 .\r\n"
                    b"drwxr-xr-x 8 root      root         4096 Dec 22 12:30 ..\r\n"
                    b"-rw-r--r-- 1 corpuser1 thecorpusers 1234 Dec 22 12:34 jumpbox1.conf\r\n"
                    b"-rw-r--r-- 1 root      root          456 Dec 22 12:34 passwd\r\n"
                    b"-rw------- 1 corpuser1 thecorpusers 7890 Dec 22 12:34 rsa_id\r\n"
                )

            elif cmd in ('cat passwd', 'cat /etc/passwd'):
                response = (
                    b"\r\nroot:x:0:0:root:/root:/bin/bash\r\n"
                    b"daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\r\n"
                    b"corpuser1:x:1001:1001:Corporate User 1:/home/corpuser1:/bin/bash\r\n"
                    b"johndoe:x:1002:1002:John Doe:/home/johndoe:/bin/bash\r\n"
                    b"janedoe:x:1003:1003:Jane Doe:/home/janedoe:/bin/bash\r\n"
                    b"guest:x:1004:1004:Guest User:/home/guest:/bin/bash\r\n"
                )

            elif cmd == 'cat /etc/shadow':
                response = b"\r\ncat: /etc/shadow: Permission denied\r\n"

            elif cmd == 'cat jumpbox1.conf':
                response = (
                    b"\r\nhost=10.0.0.5\r\n"
                    b"port=22\r\n"
                    b"user=admin\r\n"
                )

            elif cmd == 'cat /etc/os-release':
                response = (
                    b"\r\nNAME=\"Ubuntu\"\r\n"
                    b"VERSION=\"22.04.3 LTS (Jammy Jellyfish)\"\r\n"
                    b"ID=ubuntu\r\n"
                    b"ID_LIKE=debian\r\n"
                    b"PRETTY_NAME=\"Ubuntu 22.04.3 LTS\"\r\n"
                    b"VERSION_ID=\"22.04\"\r\n"
                )

            elif cmd == 'cat /etc/hosts':
                response = (
                    b"\r\n127.0.0.1   localhost\r\n"
                    b"127.0.1.1   corporate-jumpbox2\r\n"
                    b"10.0.0.1    gateway\r\n"
                    b"10.0.0.5    db-server\r\n"
                    b"10.0.0.10   web-server\r\n"
                )

            elif cmd in ('uname -a', 'uname'):
                response = b"\r\nLinux corporate-jumpbox2 5.15.0-91-generic #101-Ubuntu SMP Tue Nov 14 13:30:08 UTC 2023 x86_64 x86_64 x86_64 GNU/Linux\r\n"

            elif cmd == 'uname -r':
                response = b"\r\n5.15.0-91-generic\r\n"

            elif cmd == 'uptime':
                response = b"\r\n 10:15:30 up 47 days,  3:22,  1 user,  load average: 0.08, 0.03, 0.01\r\n"

            elif cmd == 'w':
                response = (
                    b"\r\n 10:15:30 up 47 days,  3:22,  1 user,  load average: 0.08, 0.03, 0.01\r\n"
                    b"USER     TTY      FROM             LOGIN@   IDLE JCPU   PCPU WHAT\r\n"
                    b"corpuser1 pts/0   192.168.1.50     09:01    0.00s  0.05s  0.01s w\r\n"
                )

            elif cmd == 'ps aux':
                response = (
                    b"\r\nUSER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND\r\n"
                    b"root         1  0.0  0.1  22556  1256 ?        Ss   Oct09   0:05 /sbin/init\r\n"
                    b"root       256  0.1  0.3  72312  4456 ?        S    Oct09   1:12 /usr/sbin/sshd -D\r\n"
                    b"corpuser1  801  0.0  0.1  20248  1368 pts/0    Ss   10:01   0:00 -bash\r\n"
                    b"corpuser1  900  0.0  0.0  17456   872 pts/0    R+   10:15   0:00 ps aux\r\n"
                )

            elif cmd == 'top':
                response = (
                    b"\r\ntop - 10:15:30 up 47 days,  3:22,  1 user,  load average: 0.08, 0.03, 0.01\r\n"
                    b"Tasks:  98 total,   1 running,  97 sleeping,   0 stopped,   0 zombie\r\n"
                    b"%Cpu(s):  0.3 us,  0.1 sy,  0.0 ni, 99.6 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st\r\n"
                    b"MiB Mem :   1987.2 total,    412.1 free,    803.4 used,    771.7 buff/cache\r\n"
                )

            elif cmd in ('df -h', 'df'):
                response = (
                    b"\r\nFilesystem      Size  Used Avail Use% Mounted on\r\n"
                    b"udev            974M     0  974M   0% /dev\r\n"
                    b"/dev/sda1        49G   12G   35G  26% /\r\n"
                    b"tmpfs           994M     0  994M   0% /dev/shm\r\n"
                )

            elif cmd in ('free -m', 'free'):
                response = (
                    b"\r\n               total        used        free      shared  buff/cache   available\r\n"
                    b"Mem:            1987         803         412           1         771        1041\r\n"
                    b"Swap:           2047           0        2047\r\n"
                )

            elif cmd in ('env', 'printenv'):
                response = (
                    b"\r\nSHELL=/bin/bash\r\n"
                    b"TERM=xterm-256color\r\n"
                    b"USER=corpuser1\r\n"
                    b"HOME=/home/corpuser1\r\n"
                    b"PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\r\n"
                    b"PWD=/usr/local\r\n"
                )

            elif cmd == 'history':
                response = (
                    b"\r\n    1  ls -l\r\n"
                    b"    2  cat jumpbox1.conf\r\n"
                    b"    3  ssh admin@10.0.0.5\r\n"
                    b"    4  df -h\r\n"
                    b"    5  ps aux\r\n"
                    b"    6  exit\r\n"
                )

            elif cmd == 'crontab -l':
                response = (
                    b"\r\n*/5 * * * * /usr/local/bin/health_check.sh\r\n"
                    b"0 2 * * * /usr/local/bin/backup.sh\r\n"
                )

            elif cmd == 'sudo -l':
                response = b"\r\nSorry, user corpuser1 may not run sudo on corporate-jumpbox2.\r\n"

            elif cmd.startswith('sudo '):
                response = b"\r\n[sudo] password for corpuser1: \r\nSorry, try again.\r\n"

            elif cmd in ('netstat', 'netstat -an'):
                response = (
                    b"\r\nActive Internet connections\r\n"
                    b"Proto Recv-Q Send-Q Local Address           Foreign Address         State\r\n"
                    b"tcp        0      0 0.0.0.0:22              0.0.0.0:*               LISTEN\r\n"
                    b"tcp        0      0 192.168.1.100:22        192.168.1.50:49832      ESTABLISHED\r\n"
                )

            elif cmd in ('ss -tulwn', 'ss -tuln'):
                response = (
                    b"\r\nNetid  State   Recv-Q  Send-Q  Local Address:Port  Peer Address:Port\r\n"
                    b"tcp    LISTEN  0       128     0.0.0.0:22             0.0.0.0:*\r\n"
                    b"tcp    LISTEN  0       128     0.0.0.0:80             0.0.0.0:*\r\n"
                )

            elif cmd == 'ifconfig':
                response = (
                    b"\r\neth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500\r\n"
                    b"        inet 192.168.1.100  netmask 255.255.255.0  broadcast 192.168.1.255\r\n"
                    b"        inet6 fe80::a00:27ff:fe4e:66b2  prefixlen 64  scopeid 0x20<link>\r\n"
                    b"        ether 08:00:27:4e:66:b2  txqueuelen 1000  (Ethernet)\r\n"
                    b"        RX packets 105123  bytes 14228754 (14.2 MB)\r\n"
                    b"        TX packets 50012  bytes 5634823 (5.6 MB)\r\n"
                )

            elif cmd in ('ip addr', 'ip a'):
                response = (
                    b"\r\n1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN\r\n"
                    b"    inet 127.0.0.1/8 scope host lo\r\n"
                    b"2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP\r\n"
                    b"    inet 192.168.1.100/24 brd 192.168.1.255 scope global dynamic eth0\r\n"
                )

            elif cmd.startswith('curl ') or cmd.startswith('wget '):
                response = b"\r\ncurl: (6) Could not resolve host\r\n"

            elif cmd.startswith('echo '):
                echo_content = cmd[5:].encode('utf-8', errors='replace')
                response = b"\r\n" + echo_content + b"\r\n"

            elif cmd.startswith('find '):
                response = (
                    b"\r\nfind: '/proc/tty/driver': Permission denied\r\n"
                    b"find: '/root': Permission denied\r\n"
                )

            elif cmd.startswith('cd') or cmd == '':
                response = b""

            else:
                response = b"\r\n" + cmd.encode('utf-8', errors='replace') + b": command not found\r\n"

            channel.send(response)
            channel.send(b"corporate-jumpbox2$ ")
            command = b""

def client_handle(client, addr, username, password, tarpit=False):
    client_ip = addr[0]
    print(f"{client_ip} connected to server.")
    try:
        transport = paramiko.Transport(client)
        transport.local_version = SSH_BANNER

        server = Server(client_ip=client_ip, input_username=username, input_password=password)
        transport.add_server_key(host_key)
        transport.start_server(server=server)

        channel = transport.accept(100)

        if channel is None:
            print("No channel was opened.")

        standard_banner = "Welcome to Ubuntu 22.04 LTS (Jammy Jellyfish)!\r\n\r\n"

        try:
            if tarpit:
                # Drip one character every 8 seconds — ties up automated scanners for the duration of the banner
                endless_banner = standard_banner * 100
                for char in endless_banner:
                    channel.send(char)
                    time.sleep(8)
            else:
                channel.send(standard_banner)
            emulated_shell(channel, client_ip=client_ip)

        except Exception as error:
            print(error)

    except Exception as error:
        print(error)

    finally:
        try:
            transport.close()
        except Exception:
            pass
        client.close()


def honeypot(address, port, username, password, tarpit=False):
    socks = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # SO_REUSEADDR lets the server restart immediately without waiting for sockets in TIME_WAIT
    socks.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    socks.bind((address, port))

    socks.listen(100)
    print(f"SSH server is listening on port {port}.")

    while True:
        try:
            client, addr = socks.accept()
            ssh_honeypot_thread = threading.Thread(target=client_handle, args=(client, addr, username, password, tarpit))
            ssh_honeypot_thread.start()

        except Exception as error:
            print("!!! Exception - Could not open new client connection !!!")
            print(error)