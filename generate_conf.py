#! python
from ansible.parsing.dataloader import DataLoader
from ansible.inventory.manager import InventoryManager

def generate_conf(nodes,services_nodes,peers  = 5):
    all_nodes = nodes + service_nodes
    ns = len(all_nodes)
    temp_list = all_nodes + all_nodes
    config ={}
    for idx,ip in enumerate(all_nodes):
        config[ip] = {"peers":temp_list[idx+1 :idx+1 + peers]}
    return config

if __name__ == '__main__':
    inventory_file_name = 'ansible/inventory/hosts'
    data_loader = DataLoader()
    inventory = InventoryManager(loader = data_loader,
                             sources=[inventory_file_name])

    nodes = inventory.get_groups_dict()['nodes']
    service_nodes = inventory.get_groups_dict()['service_nodes']
    configs = generate_conf(nodes,service_nodes)
    print(configs)

