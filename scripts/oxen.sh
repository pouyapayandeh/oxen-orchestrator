#!/bin/bash
oxen_core_version="my-9.2.0"
storage_server_version="my-2.2.0"
export DEBIAN_FRONTEND=noninteractive
# Check if the number of command line arguments is not equal to 1
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <init|update|compile>"
    exit 1
fi

# Read the command line argument
action=$1

# Perform actions based on the argument
case $action in
    "fix")
        # Use apt
        apt remove  -y liboxenmq-dev  

        ;;

    "init")
        # Use apt
        apt-get update
        apt --no-install-recommends -y install git wget unzip curl ca-certificates lsb-release build-essential cmake pkg-config libboost-all-dev libzmq3-dev libsodium-dev libunwind8-dev liblzma-dev libreadline6-dev doxygen graphviz libpgm-dev libsqlite3-dev libcurl4-openssl-dev 
        curl -so /etc/apt/trusted.gpg.d/oxen.gpg https://deb.oxen.io/pub.gpg && \
        echo "deb https://deb.oxen.io $(lsb_release -sc) main" |  tee /etc/apt/sources.list.d/oxen.list && \
        apt-get update && \
        apt-get --no-install-recommends -y install libssl-dev libunbound-dev nettle-dev 
        ;;
        
    "update")
        # Git clone
        mkdir -p oxen
        cd oxen
        echo "Updating oxen-core repo to ${oxen_core_version}"
        if [ ! -d "oxen-core" ]; then
            # If the folder doesn't exist, clone the repository
            git clone https://github.com/pouyapayandeh/oxen-core.git
            echo "Oxen cloned successfully."
        fi
        cd oxen-core
        git checkout $oxen_core_version
        git pull
        git submodule update --init --recursive
        cd ..
        echo "Updating oxen-storage-server repo to ${oxen_core_version}"
        if [ ! -d "oxen-storage-server" ]; then
            # If the folder doesn't exist, clone the repository
            git clone https://github.com/pouyapayandeh/oxen-storage-server.git
            echo "Oxen cloned successfully."
        fi
        cd oxen-storage-server
        git checkout $storage_server_version
        git pull
        git submodule update --init --recursive

        ;;

    "compile-core")
        # Run some command for compilation
        echo "Compiling oxen-core" && \
        mkdir -p oxen/oxen-core/build && \
        cd oxen/oxen-core/build && \
        cmake .. && \
        make -j2

        ;;

    "clean-core")
        rm -rf oxen/oxen-core/build

        ;;

    "clean-storage")
        rm -rf oxen/oxen-storage-server/build

        ;;

    "compile-storage")
        export OPENSSL_ROOT_DIR=~/oxen/openssl-1.1.1w
        echo "Compiling oxen-storage"  && \
        mkdir -p oxen/oxen-storage-server/build  && \
        cd oxen/oxen-storage-server/build && \
        cmake -DCMAKE_BUILD_TYPE=Release .. && \
        make -j2

        ;;

    "compile-ssl")
        mkdir -p oxen && cd oxen && \
        wget https://www.openssl.org/source/openssl-1.1.1w.tar.gz  && \
        tar xvf openssl-1.1.1w.tar.gz  && \
        cd openssl-1.1.1w && \
        ./config && \
        make
        ;;
    *)
        # Handle unknown argument
        echo "Unknown argument: $action. Supported arguments are init, update, compile."
        exit 1
        ;;
esac

# Exit with success
exit 0