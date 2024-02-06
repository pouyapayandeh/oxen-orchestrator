#! python
import os
import paramiko
from contextlib import closing
import paramiko
import time
servers = {} # read from private

def connect(server, username, password,port =2200):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, username=username, password=password,port=port)
    return client


def wait_until_channel_endswith(channel, endswith, wait_in_seconds=15):
    """Continues execution if the specified string appears at the end of the channel

    Raises: TimeoutError if string cannot be found on the channel
    """

    timeout = time.time() + wait_in_seconds
    read_buffer = b''
    while not read_buffer.endswith(endswith):
        if channel.recv_ready():
           read_buffer += channel.recv(4096)
        elif time.time() > timeout:
            raise TimeoutError(f"Timeout while waiting for '{endswith}' on the channel")
        else:
            time.sleep(1)

def change_expired_password_over_ssh(host, username, current_password, new_password):
    """Changes expired password over SSH with paramiko"""
    with closing(paramiko.SSHClient()) as ssh_connection:
        ssh_connection.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_connection.connect(hostname=host, username=username, password=current_password,port=2200)
        ssh_channel = ssh_connection.invoke_shell()

        wait_until_channel_endswith(ssh_channel, b'Current password: ')
        ssh_channel.send(f'{current_password}\n')

        wait_until_channel_endswith(ssh_channel, b'New password: ')
        ssh_channel.send(f'{new_password}\n')

        wait_until_channel_endswith(ssh_channel, b'Retype new password: ')
        ssh_channel.send(f'{new_password}\n')

def deploy_key(key, server, username, password):
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, username=username, password=password,port=2200)
    client.exec_command('mkdir -p ~/.ssh/')
    client.exec_command('echo "%s" > ~/.ssh/authorized_keys' % key)
    client.exec_command('chmod 644 ~/.ssh/authorized_keys')
    client.exec_command('chmod 700 ~/.ssh/')

key = open(os.path.expanduser('~/.ssh/id_rsa.pub')).read()
for server in servers['servers'].values():
    print(f"{server['ip']} ansible_port=2200 ansible_user=root")
    # deploy_key(key,server=server['ip'],username=server['user'],password=server['password'])
    # print("Key deployed")



