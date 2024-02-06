#! python
from ansible.parsing.dataloader import DataLoader
from ansible.inventory.manager import InventoryManager
import paramiko
import ansible_runner

    # print(service_nodes)
    # clients = []
    # for sn in nodes:
    #     client = connect(sn,'root')
    #     clients.append(client) 
    #     print(f"connected to {sn}")
    
    # for client in clients:
    #     stdin, stdout, stderr = client.exec_command("ls /")
    #     print("Run ls",stdout.readlines())

    # r = ansible_runner.run(private_data_dir='ansible', playbook='setup.yml')
    # print("{}: {}".format(r.status, r.rc))

def connect(server, username,port =2200):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, username=username,port=port)
    return client

if __name__ == '__main__':
    inventory_file_name = 'ansible/inventory/hosts'
    data_loader = DataLoader()
    inventory = InventoryManager(loader = data_loader,
                             sources=[inventory_file_name])

    nodes = inventory.get_groups_dict()['nodes']
    service_nodes = inventory.get_groups_dict()['service_nodes']
    print(nodes)

