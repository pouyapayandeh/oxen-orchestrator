#!/usr/bin/python3

from http.client import RemoteDisconnected
import os
import sys
import random
from threading import Thread
import requests
import subprocess
import time
from ssh_utils import connect


class ProcessExited(RuntimeError):
    pass


class TransferFailed(RuntimeError):
    def __init__(self, message, json):
        super().__init__(message)
        self.message = message
        self.json = json

def retry(times, exceptions):
    """
    Retry Decorator
    Retries the wrapped function/method `times` times if the exceptions listed
    in ``exceptions`` are thrown
    :param times: The number of times to repeat the wrapped function/method
    :type times: Int
    :param Exceptions: Lists of exceptions that trigger a retry attempt
    :type Exceptions: Tuple of Exceptions
    """
    def decorator(func):
        def newfn(*args, **kwargs):
            attempt = 0
            while attempt < times:
                try:
                    return func(*args, **kwargs)
                except exceptions:
                    print(
                        'Exception thrown when attempting to run %s, attempt '
                        '%d of %d' % (func, attempt, times)
                    )
                    print(*args, **kwargs)
                    attempt += 1
            return func(*args, **kwargs)
        return newfn
    return decorator

class RPCDaemon:
    def __init__(self,name,remote_ip,verbose=False):
        self.name = name
        self.client = None
        self.remote_ip = remote_ip
        self.terminated = False
        self.verbose = verbose


    def __del__(self):
        self.stop()


    def terminate(self, repeat=False):
        """Sends a TERM signal if one hasn't already been sent (or even if it has, with
        repeat=True).  Does not wait for exit."""
        # if self.proc and (repeat or not self.terminated):
        #     self.proc.terminate()
        self.terminated = True
        print("Terminating",self.name,self.remote_ip)
        if self.t.is_alive():
            self.t.join(1)
        self.client.close()

    def log(self):
        if not os.path.exists("logs/"):
            os.makedirs("logs/")
        with open("logs/"+self.name+"@"+self.remote_ip,"w") as f:
            while not self.terminated:
                line = self.stdout.readline()
                f.write(line)
            
    def start(self,screen = True):
        self.client = connect(self.remote_ip)
        args = self.arguments()
        cmdline =" ".join(args)
        cmdline = "screen " + cmdline
        print(cmdline)
        self.stdin,self.stdout,self.stderr = self.client.exec_command(cmdline, get_pty=True )
        self.terminated = False
        self.t = Thread(target = self.log, args = (),daemon=True)
        
        self.t.start()


    def stop(self):
        """Tries stopping with a term at first, then a kill if the term hasn't worked after 10s"""
        print("Stopping",flush=True)
        if self.client or self.t.is_alive():
            self.terminate()
        #     try:
        #         self.proc.wait(timeout=10)
        #     except subprocess.TimeoutExpired:
        #         print("{} took more than 10s to exit, killing it".format(self.name))
        #         self.proc.kill()
        #     self.proc = None


    def arguments(self):
        """Returns the startup arguments; default is just self.args, but subclasses can override."""
        return self.args

    @retry(times=3, exceptions=(Exception))
    def json_rpc(self, method, params=None, *, timeout=60):
        """Sends a json_rpc request to the rpc port.  Returns the response object."""
        if not self.client:
            raise RuntimeError("Cannot make rpc request before calling start()")
        json = {
                "jsonrpc": "2.0",
                "id": "0",
                "method": method,
                }
        if params:
            json["params"] = params
        return requests.post('http://{}:{}/json_rpc'.format(self.listen_ip, self.rpc_port), json=json, timeout=timeout)
    @retry(times=3, exceptions=(Exception))
    def rpc(self, path, params=None, *, timeout=60):
        """Sends a non-json_rpc rpc request to the rpc port at path `path`, e.g. /get_info.  Returns the response object."""
        if not self.client:
            raise RuntimeError("Cannot make rpc request before calling start()")
        return requests.post('http://{}:{}{}'.format(self.listen_ip, self.rpc_port, path), json=params, timeout=timeout)


    def wait_for_json_rpc(self, method, params=None, *, timeout=60):
        """Calls `json_rpc', sleeping if it fails for up time `timeout' seconds.  Returns the
        response if it succeeds, raises the last exception if timeout is reached.  If the process
        exit, raises a RuntimeError"""

        until = time.time() + timeout
        now = time.time()
        while now < until:
            # exit_status = self.proc.poll()
            # if exit_status is not None:
            #     raise ProcessExited("{} exited ({}) while waiting for an RPC response".format(self.name, exit_status))

            timeout = until - now
            try:
                return self.json_rpc(method, params, timeout=timeout)
            except:
                if time.time() + .25 >= until:
                    raise
                time.sleep(.25)
                now = time.time()
                if now >= until:
                    raise

class StorageService(RPCDaemon):
        # ./httpserver/oxen-storage 127.51.143.46 1234 --bind-ip 127.51.143.46 --data-dir=./data 
# --oxend-rpc  ipc:///home/pouya/projects/sarbazi/oxen-orchestrator/testdata/oxen-127.51.143.46-1100/devnet/oxend.sock 
# --omq-port 2226
    def __init__(self, *,
        storage = "oxen-storage",
        name=None, 
        oxend_ip=None,
        listen_ip=None,
        rpc_port=None, 
        omq_port=None,
        oxen_rpc=None,
        datadir=None,
        verbose = False):
        self.rpc_port = rpc_port
        if name is None:
            name = 'storage@{}'.format(self.rpc_port)
        super().__init__(name,listen_ip,verbose=verbose)
        self.listen_ip = listen_ip 
        self.omq_port = omq_port 
        self.oxen_rpc = oxen_rpc
        self.oxend_ip = oxend_ip
        self.path = '{}/storage-{}-{}'.format( datadir or '.', self.listen_ip, self.rpc_port)
        # + list(self.__class__.base_args)
        self.args = [storage] 
        self.args += (
                "0.0.0.0",
                str(self.rpc_port),
                '--bind-ip={}'.format("0.0.0.0"),
                '--data-dir={}'.format(self.path),
                '--oxend-rpc={}'.format(self.oxen_rpc),
                '--omq-port={}'.format(self.omq_port),
                )
        print(' '.join(self.args))
            

class Daemon(RPCDaemon):
    base_args = ('--dev-allow-local-ips', '--fixed-difficulty=1', '--devnet', '--non-interactive')

    def __init__(self, *,
            oxend='oxend',
            listen_ip=None, p2p_port=None, rpc_port=None, zmq_port=None, qnet_port=None, ss_port=None,
            name=None,
            datadir=None,
            service_node=False,
            log_level=2,
            peers=()):
        self.rpc_port = rpc_port 
        if name is None:
            name = 'oxend@{}'.format(self.rpc_port)
        super().__init__(name,listen_ip)
        self.listen_ip = listen_ip 
        self.p2p_port = p2p_port 
        self.zmq_port = zmq_port 
        self.qnet_port = qnet_port
        self.ss_port = ss_port 
        self.peers = []
        self.path = '{}/oxen-{}-{}'.format(datadir or '.', self.listen_ip, self.rpc_port)
        self.args = [oxend] + list(self.__class__.base_args)
        self.args += (
                '--data-dir={}'.format(self.path),
                '--log-level={}'.format(log_level),
                '--log-file=oxen.log'.format(self.listen_ip, self.p2p_port),
                '--p2p-bind-ip={}'.format("0.0.0.0"),
                '--p2p-bind-port={}'.format(self.p2p_port),
                '--rpc-admin={}:{}'.format("0.0.0.0", self.rpc_port),
                '--quorumnet-port={}'.format(self.qnet_port),
                )

        for d in peers:
            self.add_peer(d)

        if service_node:
            self.args += (
                    '--service-node',
                    '--service-node-public-ip={}'.format(self.listen_ip),
                    '--storage-server-port={}'.format(self.ss_port),
                    )


    def arguments(self):
        return self.args + [
            '--add-exclusive-node={}:{}'.format(node.listen_ip, node.p2p_port) for node in self.peers]


    def ready(self):
        """Waits for the daemon to get ready, i.e. for it to start returning something to a
        `get_info` rpc request.  Calls start() if it hasn't already been called."""
        if not self.client:
            self.start()
        self.wait_for_json_rpc("get_info")


    def add_peer(self, node):
        """Adds a peer.  Must be called before starting."""
        if self.client:
            raise RuntimeError("add_peer needs to be called before start()")
        self.peers.append(node)


    def remove_peer(self, node):
        """Removes a peer.  Must be called before starting."""
        if self.client:
            raise RuntimeError("remove_peer needs to be called before start()")
        self.peers.remove(node)


    def mine_blocks(self, num_blocks, wallet, *, slow=True):
        a = wallet.address()
        self.rpc('/start_mining', {
            "miner_address": a,
            "threads_count": 1,
            "num_blocks": num_blocks,
            "slow_mining": slow
        })


    def height(self):
        return self.rpc("/get_height").json()["height"]


    def txpool_hashes(self):
        return [x['id_hash'] for x in self.rpc("/get_transaction_pool").json()['transactions']]


    def ping(self, *, storage=True, lokinet=True):
        """Sends fake storage server and lokinet pings to the running oxend"""
        if storage:
            self.json_rpc("storage_server_ping", { "version_major": 2, "version_minor": 2, "version_patch": 0 })
        if lokinet:
            self.json_rpc("lokinet_ping", { "version": [9,9,9] })

    def send_uptime_proof(self):
        """Triggerst test uptime proof"""
        self.json_rpc("test_trigger_uptime_proof")


    def p2p_resync(self):
        """Triggers a p2p resync to happen soon (i.e. at the next p2p idle loop)."""
        self.json_rpc("test_trigger_p2p_resync")



class Wallet(RPCDaemon):
    base_args = ('--disable-rpc-login', '--non-interactive', '--password','abcd', '--devnet', '--disable-rpc-long-poll',
 '--daemon-ssl=disabled',"--confirm-external-bind")

    def __init__(
            self,
            node,
            *,
            rpc_wallet='oxen-wallet-rpc',
            name=None,
            datadir=None,
            listen_ip=None,
            rpc_port=None,
            log_level=2):

        self.listen_ip = listen_ip
        self.rpc_port = rpc_port 
        self.node = node

        self.name = name or 'wallet@{}'.format(self.rpc_port)
        super().__init__(self.name,listen_ip)

        self.walletdir = '{}/wallet-{}-{}'.format(datadir or '.', self.listen_ip, self.rpc_port)
        self.args = [rpc_wallet] + list(self.__class__.base_args)
        self.args += (
                '--rpc-bind-ip={}'.format("0.0.0.0"),
                '--rpc-bind-port={}'.format(self.rpc_port),
                '--log-level={}'.format(log_level),
                '--log-file={}/log.txt'.format(self.walletdir),
                '--daemon-address={}:{}'.format("127.0.0.1", node.rpc_port),
                '--wallet-dir={}'.format(self.walletdir),
                )
        self.wallet_address = None


    def ready(self, wallet="wallet", existing=False):
        """Makes the wallet ready, waiting for it to start up and create a new wallet (or load an
        existing one, if `existing`) within the rpc wallet.  Calls `start()` first if it hasn't
        already been called.  Does *not* explicitly refresh."""

        if not self.client:
            self.start()

        self.wallet_filename = wallet
        if existing:
            r = self.wait_for_json_rpc("open_wallet", {"filename": wallet, "password": ""})
        else:
            r = self.wait_for_json_rpc("create_wallet", {"filename": wallet, "password": "", "language": "English"})
        if 'result' not in r.json():
            print(r.json())
            raise RuntimeError("Cannot open or create wallet: {}".format(r['error'] if 'error' in r else 'Unexpected response: {}'.format(r)))
        print('Started RPC Wallet - {}, on {}:{}'.format(self.name, self.listen_ip, self.rpc_port))


    def refresh(self):
        return self.json_rpc('refresh')


    def address(self):
        if not self.wallet_address:
            self.wallet_address = self.json_rpc("get_address").json()["result"]["address"]

        return self.wallet_address


    def new_wallet(self):
        self.wallet_address = None
        r = self.wait_for_json_rpc("close_wallet")
        if 'result' not in r.json():
            raise RuntimeError("Cannot close current wallet: {}".format(r['error'] if 'error' in r else 'Unexpected response: {}'.format(r)))
        if not hasattr(self, 'wallet_suffix'):
            self.wallet_suffix = 2
        else:
            self.wallet_suffix += 1
        r = self.wait_for_json_rpc("create_wallet", {"filename": "{}_{}".format(self.wallet_filename, self.wallet_suffix), "password": "", "language": "English"})
        if 'result' not in r.json():
            raise RuntimeError("Cannot create wallet: {}".format(r['error'] if 'error' in r else 'Unexpected response: {}'.format(r)))


    def balances(self, refresh=False):
        """Returns (total, unlocked) balances.  Can optionally refresh first."""
        if refresh:
            self.refresh()
        b = self.json_rpc("get_balance").json()['result']
        return (b['balance'], b['unlocked_balance'])


    def transfer(self, to, amount=None, *, priority=None, sweep=False):
        """Attempts a transfer.  Throws TransferFailed if it gets rejected by the daemon, otherwise
        returns the 'result' key."""
        if priority is None:
            priority = 1
        if sweep and not amount:
            r = self.json_rpc("sweep_all", {"address": to.address(), "priority": priority})
        elif amount and not sweep:
            r = self.json_rpc("transfer_split", {"destinations": [{"address": to.address(), "amount": amount}], "priority": priority})
        else:
            raise RuntimeError("Wallet.transfer: either `sweep` or `amount` must be given")

        r = r.json()
        if 'error' in r:
            raise TransferFailed("Transfer failed: {}".format(r['error']['message']), r)
        return r['result']


    def find_transfers(self, txids, in_=True, pool=True, out=True, pending=False, failed=False):
        transfers = self.json_rpc('get_transfers', {'in':in_, 'pool':pool, 'out':out, 'pending':pending, 'failed':failed }).json()['result']
        def find_tx(txid):
            for type_, txs in transfers.items():
                for tx in txs:
                    if tx['txid'] == txid:
                        return tx
        return [find_tx(txid) for txid in txids]


    def register_sn(self, sn):
        r = sn.json_rpc("get_service_node_registration_cmd", {
            "operator_cut": "100",
            "contributions": [{"address": self.address(), "amount": 100000000000}],
            "staking_requirement": 100000000000
        }).json()
        if 'error' in r:
            raise RuntimeError("Registration cmd generation failed: {}".format(r['error']['message']))
        cmd = r['result']['registration_cmd']
        r = self.json_rpc("register_service_node", {"register_service_node_str": cmd}).json()
        if 'error' in r:
            raise RuntimeError("Failed to submit service node registration tx: {}".format(r['error']['message']))
