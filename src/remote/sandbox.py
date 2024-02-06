#! python
from concurrent.futures import ALL_COMPLETED, ThreadPoolExecutor, wait
import os
from remote_daemons import Daemon
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

parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('--log', choices = ["DEBUG","INFO","TRACE","WARNING"],default="INFO")
parser.add_argument('--sum', dest='accumulate', action='store_const',
                    const=sum, default=max,
                    help='sum the integers (default: find the max)')

args = parser.parse_args()

logger = logging.getLogger(__name__)

servers = {} # read from private

# def connect(server, username,port =2200):
#     client = paramiko.SSHClient()
#     client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#     client.connect(server, username=username,port=port)
#     return client
# client = connect("37.27.43.50","root")
# stdin, stdout, stderr  = client.exec_command("cat")
# print(stdout.readlines())



# stdout =daemon.stdout
# stderr =daemon.stderr
# l = 0
# while l<100:
#     l+=1
#     # print(".")
#     if len(stdout.channel.in_buffer):
#         print(stdout.readline(),end="")
#     # if len(stderr.channel.in_buffer):
#     #     print(stderr.readline())
#     time.sleep(0.1)

# print(daemon.wait_for_json_rpc("get_info").content)

# input("Use Ctrl-C to exit...")
# loop = asyncio.get_event_loop()
# try:
#     loop.run_forever()
# except KeyboardInterrupt:
#     print(f'!!! AsyncApplication.run: got KeyboardInterrupt during start')
# finally:
#     loop.close()

def exec_on_host(server,cmd):
    logger.info(f"running {cmd} on {server}")
    client = connect(server)
    _, stdout, _ = client.exec_command(cmd)
    stdout.channel.recv_exit_status()
    client.close()
def run_ssn(bin_path,ss_binpath,datadirectory,nodes,service_nodes):
    
    logger.info("Clearing Data dirs")
    servers = nodes + service_nodes
    cmd = "rm -rf ~/oxen/datadir/*"
    executor = ThreadPoolExecutor(max_workers=10)
   
    futures = [executor.submit(exec_on_host,server,cmd)  for server in servers]
    done, not_done = wait(futures, return_when=ALL_COMPLETED)

    logger.info("starting new SNN")
    
    snn = SNNetwork(datadir=datadirectory+'/',
                    binpath=bin_path,
                    ss_binpath=ss_binpath,
                    nodes=nodes,
                    sns=service_nodes
                    )
    return snn
    # logger.info("started SSN")
    # logger.info("Communicate with daemon on ip: {} RPC port: {}  P2P port: {}  ZMQ port: {}  QNET port: {}  SS port: {}"
    #             .format(snn.sns[0].listen_ip,snn.sns[0].rpc_port,
    #             snn.sns[0].p2p_port,snn.sns[0].zmq_port,snn.sns[0].qnet_port,snn.sns[0].ss_port))

if __name__ == "__main__":
    numeric_level = getattr(logging, args.log.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % args.log)
    logging.basicConfig(level=numeric_level,format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

    inventory_file_name = 'ansible/inventory/hosts'
    data_loader = DataLoader()
    inventory = InventoryManager(loader = data_loader,
                             sources=[inventory_file_name])

    nodes = inventory.get_groups_dict()['nodes']
    service_nodes = inventory.get_groups_dict()['service_nodes']
    print(nodes + service_nodes)


    # binpath = "~/oxen/oxen-core/build/bin/oxend"
    # daemon = Daemon(oxend=binpath,listen_ip="37.27.43.50",p2p_port=1000,rpc_port=1001,
    #             zmq_port=1002,qnet_port=1003,ss_port=1004,datadir="oxen/datadir")
    # daemon.start()
    

    snn = run_ssn("oxen/oxen-core/build/bin",
            "oxen/oxen-storage-server/build/httpserver",
            "oxen/testdata",nodes,service_nodes)

    print("Use Ctrl-C to exit...")
    loop = asyncio.get_event_loop()
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print(f'got KeyboardInterrupt')
    finally:
        snn.__del__()
        loop.close()
    print("Exiting")