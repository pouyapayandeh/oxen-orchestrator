#! python
from concurrent.futures import ALL_COMPLETED, ThreadPoolExecutor, wait
import os

import requests
from remote_daemons import Daemon, retry
from ssh_utils import connect
from contextlib import closing
import time
import asyncio
from remote_service_node_network import SNNetwork
import argparse
import sys
import logging
from ansible.parsing.dataloader import DataLoader
from ansible.inventory.manager import InventoryManager
from colorama import Fore, Back, Style


def exec_on_host(server,cmd):
    logging.info(Fore.YELLOW+f"running {cmd} on {server}")
    client = connect(server)
    _, stdout, _ = client.exec_command(cmd)
    stdout.channel.recv_exit_status()
    output = stdout.readlines()
    # print(output)
    client.close()
    return output

def check_remote_processes(nodes,service_nodes):

    print(Fore.BLUE+"Checking Servers for oxen") 

    servers = nodes + service_nodes
    cmd = "pgrep oxend"
    executor = ThreadPoolExecutor(max_workers=10)   
    futures = [executor.submit(exec_on_host,server,cmd)  for server in servers]
    done, not_done = wait(futures, return_when=ALL_COMPLETED)
    for idx,(server,pid) in enumerate(zip(servers,futures),1):
        if len(pid.result()) > 0:
            print(Fore.WHITE +f"{idx}\t",server,Fore.GREEN+"[Oxen is Running]")
        else:
            print(Fore.WHITE +f"{idx}\t", server,Fore.RED+"[Oxen is not Running]")

    print(Fore.BLUE+"Checking Servers for storage") 
    cmd = "pgrep oxen-storage"
    futures = [executor.submit(exec_on_host,server,cmd)  for server in servers]
    done, not_done = wait(futures, return_when=ALL_COMPLETED)
    for idx,(server,pid) in enumerate(zip(servers,futures),1):
        if len(pid.result()) > 0:
            print(Fore.WHITE +f"{idx}\t",server,Fore.GREEN+"[Storage is Running]")
        else:
            print(Fore.WHITE +f"{idx}\t", server,Fore.RED+"[Storage is not Running]")

    print(Fore.BLUE+"Checking Servers for wallet") 
    cmd = "pgrep oxen-wallet-rpc"
    futures = [executor.submit(exec_on_host,server,cmd)  for server in servers]
    done, not_done = wait(futures, return_when=ALL_COMPLETED)
    for idx,(server,pid) in enumerate(zip(servers,futures),1):
        if len(pid.result()) > 0:
            print(Fore.WHITE +f"{idx}\t",server,Fore.GREEN+"[Wallet is Running]")
        else:
            print(Fore.WHITE +f"{idx}\t", server,Fore.RED+"[Wallet is not Running]")

@retry(times=3, exceptions=(Exception))
def json_rpc(listen_ip,rpc_port, method, params=None, *, timeout=60):
    json = {
            "jsonrpc": "2.0",
            "id": "0",
            "method": method,
            }
    if params:
        json["params"] = params
    return requests.post('http://{}:{}/json_rpc'.format(listen_ip, rpc_port), json=json, timeout=timeout)

@retry(times=3, exceptions=(Exception))
def rpc(listen_ip,rpc_port, path, params=None, *, timeout=60):
    return requests.post('http://{}:{}{}'.format(listen_ip, rpc_port, path), json=params, timeout=timeout)

def check_oxen_rpcs(nodes,service_nodes):
    # servers = nodes + service_nodes
    for s in service_nodes:
        try:
            res = json_rpc(s,1001,"get_service_node_status").json()
            print(res)
            print(Fore.GREEN+f"[{s}]"+Fore.WHITE)
            print(f"swarm id = {res['result']['service_node_state']['swarm_id']}")
            print(f"activation = {res['result']['service_node_state']['active']}")
            print(f"storage_port = {res['result']['service_node_state']['storage_port']}")
            print(f"quorumnet_port = {res['result']['service_node_state']['quorumnet_port']}")
            print(f"activation = {res['result']['service_node_state']['active']}")
        except:
            print(Fore.RED+f'{s} RPC Error')
    print("Get Info")
    for d in service_nodes:
        print(json_rpc(s,1001,"get_info").json())

if __name__ == "__main__":

    inventory_file_name = 'ansible/inventory/hosts'
    data_loader = DataLoader()
    inventory = InventoryManager(loader = data_loader,
                             sources=[inventory_file_name])

    nodes = inventory.get_groups_dict()['nodes']
    service_nodes = inventory.get_groups_dict()['service_nodes']
    print(nodes + service_nodes)



    check_remote_processes(nodes,service_nodes)
    check_oxen_rpcs(nodes,service_nodes)
    # check_remote_processes("oxen/oxen-core/build/bin",
    #         "oxen/oxen-storage-server/build/httpserver",
    #         "oxen/testdata",nodes,service_nodes)