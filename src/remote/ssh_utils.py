
import paramiko

def connect(server, username = "root",port =2200):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, username=username,port=port)
    return client

def exec_on_hosts(servers,cmd,username = "root",port =2200):
    for server in servers:
        client = connect(server,cmd,username=username,port=port)
        stdin, stdout, stderr = client.exec_command()
        stdout.channel.recv_exit_status()