#!/bin/sh
# Start up Soyuz for local testing on a dev machine.

start_twistd() {
    # Start twistd for service $1.
    mkdir -p "/var/tmp/$1"
    echo "Starting $1."
    bin/twistd \
        --logfile "/var/tmp/development-$1.log" \
        --pidfile "/var/tmp/development-$1.pid" \
        -y "$2"
}

start_twistd testkeyserver lib/lp/testing/keyserver/testkeyserver.tac
start_twistd buildd-manager daemons/buildd-manager.tac
mkdir -p /var/tmp/poppy
export POPPY_ROOT=/var/tmp/poppy/incoming
start_twistd poppy-sftp daemons/poppy-sftp.tac


echo "Done."
