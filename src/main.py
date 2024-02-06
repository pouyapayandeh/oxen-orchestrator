#! python
import sys
import logging
import argparse
import os
import subprocess
import shutil
import asyncio
from local.service_node_network import SNNetwork
OXEN_CORE_REPO = "git@github.com:pouyapayandeh/oxen-core.git"
OXEN_CORE_LOCAL_PATH = "oxen-core"

PATH = "./"


parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('--log', choices = ["DEBUG","INFO","TRACE","WARNING"],default="INFO")
parser.add_argument('--sum', dest='accumulate', action='store_const',
                    const=sum, default=max,
                    help='sum the integers (default: find the max)')

args = parser.parse_args()

logger = logging.getLogger(__name__)


def init_repo(repo_url,local_path,branch=""):
    if not os.path.exists(local_path):
        logger.info("repo %s at %s does not Exists",repo_url,local_path)
        logger.info("clonning repo %s",repo_url)
        subprocess.run(["git", "clone",repo_url]).check_returncode()
    if branch:
        logger.info("checking out branch")
        subprocess.run(["git", "checkout",branch],cwd=local_path).check_returncode()
        logger.info("init submodules")
        subprocess.run(["git", "submodule","update","--init","--recursive"],cwd=local_path).check_returncode()
    logger.info("repo %s inited",repo_url)

def compile_oxen(local_path,clean=False):
    build_dir = os.path.join(local_path,"build")
    bin_dir = os.path.join(build_dir,"bin")
    if not os.path.exists(build_dir):
        os.makedirs(build_dir)
    if  os.path.exists(bin_dir) and clean:
        logger.info("deleting all files in %s",bin_dir)
        shutil.rmtree(bin_dir)
    logger.info("running cmake")
    subprocess.run(["cmake", ".."],cwd=build_dir).check_returncode()
    logger.info("running make")
    subprocess.run(["make", "-j4"],cwd=build_dir).check_returncode()
    logger.info("checking if oxend exists")
    if os.path.exists(os.path.join(bin_dir,"oxend")):
        logger.info("oxend exists")
        return bin_dir
    raise FileNotFoundError("oxend not found")

def run_ssn(bin_path,datadirectory):
    if os.path.isdir(datadirectory+'/'):
        shutil.rmtree(datadirectory+'/', ignore_errors=False, onerror=None)
    logger.info("starting new SNN")
    
    snn = SNNetwork(datadir=datadirectory+'/',binpath=bin_path,ss_binpath="/home/pouya/projects/sarbazi/oxen-storage-server/build/httpserver",ss=1)
    logger.info("started SSN")
    logger.info("Communicate with daemon on ip: {} RPC port: {}  P2P port: {}  ZMQ port: {}  QNET port: {}  SS port: {}"
                .format(snn.sns[0].listen_ip,snn.sns[0].rpc_port,
                snn.sns[0].p2p_port,snn.sns[0].zmq_port,snn.sns[0].qnet_port,snn.sns[0].ss_port))
if __name__ == "__main__":
    numeric_level = getattr(logging, args.log.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % args.log)
    logging.basicConfig(level=numeric_level,format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')


    logger.info("Starting Orchestration")
    logger.info("PYTHON PATH: %s",sys.executable)
    init_repo(OXEN_CORE_REPO,OXEN_CORE_LOCAL_PATH,"my-9.2.0")

    bin_path = compile_oxen(OXEN_CORE_LOCAL_PATH)
    run_ssn("oxen-core/build/bin","testdata")

    input("Use Ctrl-C to exit...")
    loop = asyncio.get_event_loop()
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print(f'!!! AsyncApplication.run: got KeyboardInterrupt during start')
    finally:
        loop.close()