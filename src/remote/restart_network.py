#! python
from concurrent.futures import ALL_COMPLETED, ThreadPoolExecutor, wait
import os

import requests
from remote_daemons import Daemon, StorageService, Wallet, retry
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
from datetime import datetime

def exec_on_host(server,cmd):
    logging.info(Fore.YELLOW+f"running {cmd} on {server}")
    client = connect(server)
    _, stdout, _ = client.exec_command(cmd)
    stdout.channel.recv_exit_status()
    output = stdout.readlines()
    # print(output)
    client.close()
    return output

def killing_oxen(nodes,service_nodes):

    print(Fore.BLUE+"Killing Oxen") 

    servers = nodes + service_nodes
    cmd = "pkill -9 oxen-wallet-rpc \n  pkill -9 oxend \n pkill -9 oxen-storage \n "
    executor = ThreadPoolExecutor(max_workers=10)   
    futures = [executor.submit(exec_on_host,server,cmd)  for server in servers]
    done, not_done = wait(futures, return_when=ALL_COMPLETED)
    print(Fore.BLUE+"Oxen Should be Killed") 

def check_process(nodes,service_nodes):
    executor = ThreadPoolExecutor(max_workers=10)  
    servers = nodes + service_nodes
    cmd = "pgrep oxend"
    print(Fore.BLUE+"Checking if Oxen is running") 
    futures = [executor.submit(exec_on_host,server,cmd)  for server in servers]
    done, not_done = wait(futures, return_when=ALL_COMPLETED)
    for idx,(server,pid) in enumerate(zip(servers,futures),1):
        if len(pid.result()) > 0:
            print(Fore.WHITE +f"{idx}\t",server,Fore.GREEN+"[Oxen is Running]")
        else:
            print(Fore.WHITE +f"{idx}\t", server,Fore.RED+"[Oxen is not Running]")

def restart_ssn(binpath,ss_binpath,datadir,_nodes=[], _sns=[]):
    nodeopts ={"oxend":binpath+'/oxend',"p2p_port":1000,"rpc_port":1001,
            "zmq_port":1002,"qnet_port":1003,"ss_port":1004,"datadir":"oxen/datadir"} 
    sns = [Daemon(service_node=True,listen_ip=ip, **nodeopts) for ip in _sns]
    nodes = [Daemon(listen_ip=ip,**nodeopts) for ip in _nodes]

    all_nodes = sns + nodes

    wallets = []
    for idx,name in enumerate(('Alice', 'Bob', 'Mike')):
        wallets.append(Wallet(
            node=nodes[idx % len(nodes)],
            name=name,
            listen_ip=_nodes[idx % len(nodes)],
            rpc_port=2001,
            rpc_wallet=binpath+'/oxen-wallet-rpc',
            datadir=datadir))

    alice, bob, mike = wallets
    for w in wallets:
        print(Fore.GREEN+"Starting new RPC wallet {w.name} at {w.listen_ip}:{w.rpc_port}".format(w=w))
        w.start()

    for i in range(len(all_nodes)):
        for j in (2, 3, 5, 7, 11):
            k = (i + j) % len(all_nodes)
            if i != k:
                all_nodes[i].add_peer(all_nodes[k])

    print(Fore.BLUE+"Starting new oxend service nodes with RPC "+Fore.WHITE)
    for sn in sns:
        print(Fore.GREEN+f"{sn.listen_ip}:{sn.rpc_port}"+Fore.WHITE)
        sn.start()
    print(datetime.now())
    print(Fore.BLUE+"Starting new regular oxend nodes with RPC "+Fore.WHITE)
    for d in nodes:
        print(Fore.GREEN+f"{d.listen_ip}:{d.rpc_port}"+Fore.WHITE)
        d.start()

    print("Waiting for all oxend's to get ready")
    for d in all_nodes:
        d.wait_for_json_rpc("get_info")


    print(Fore.BLUE+"Starting Storage Services"+Fore.WHITE)
    ss = [StorageService(storage=ss_binpath+'/oxen-storage', datadir=datadir,oxend_ip=sn.remote_ip,
                                  listen_ip =sn.remote_ip,
                                oxen_rpc="ipc:///root/"+sn.path+"/devnet/oxend.sock"
                                ,rpc_port=1005,omq_port=1006,verbose=True) 
                for sn in sns]

    for s in ss:
        print(Fore.CYAN+"Storage @ {}".format(s.listen_ip)+Fore.WHITE)
        s.start()

    print("Sending fake lokinet/ss pings")
    for sn in sns:
        sn.ping()

    all_service_nodes_proofed = lambda sn: all(x['quorumnet_port'] > 0 for x in
            sn.json_rpc("get_n_service_nodes", {"fields":{"quorumnet_port":True}}).json()['result']['service_node_states'])

    print(Fore.BLUE+"Waiting for proofs to propagate: "+Fore.WHITE)
    for sn in sns:
        print("Node Proof from ",sn.listen_ip," is ",all_service_nodes_proofed(sn))
    time.sleep(10)
    for sn in sns:
        sn.send_uptime_proof()
    print(Fore.GREEN+"Done."+Fore.WHITE)
    

if __name__ == "__main__":

    inventory_file_name = 'ansible/inventory/hosts'
    data_loader = DataLoader()
    inventory = InventoryManager(loader = data_loader,
                             sources=[inventory_file_name])

    nodes = inventory.get_groups_dict()['nodes']
    service_nodes = inventory.get_groups_dict()['service_nodes']
    print(nodes + service_nodes)



    killing_oxen(nodes,service_nodes)
    
    check_process(nodes,service_nodes)
    exit()
    print(Fore.WHITE)
    restart_ssn("oxen/oxen-core/build/bin",
            "oxen/oxen-storage-server/build/httpserver",
            "oxen/testdata",nodes,service_nodes)
    check_process(nodes,service_nodes)
    # check_oxen_rpcs(nodes,service_nodes)
    # check_remote_processes("oxen/oxen-core/build/bin",
    #         "oxen/oxen-storage-server/build/httpserver",
    #         "oxen/testdata",nodes,service_nodes)