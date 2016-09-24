#!/bin/sh
# Start up Soyuz for local testing on a dev machine.

start_twistd() {
    # Start twistd for service $1.
    name=$1
    tac=$2
    shift 2
    mkdir -p "/var/tmp/$name"
    echo "Starting $name."
    bin/twistd \
        --logfile "/var/tmp/development-$name.log" \
        --pidfile "/var/tmp/development-$name.pid" \
        -y "$tac" $@
}

start_twistd_plugin() {
    # Start twistd for plugin service $1.
    name=$1
    plugin=$2
    shift 2
    echo "Starting $name."
    "bin/twistd-for-$name" \
        --logfile "/var/tmp/development-$name.log" \
        --pidfile "/var/tmp/development-$name.pid" \
        "$plugin" "$@"
}

start_twistd testkeyserver lib/lp/testing/keyserver/testkeyserver.tac
start_twistd buildd-manager daemons/buildd-manager.tac
mkdir -p /var/tmp/txpkgupload/incoming
start_twistd_plugin txpkgupload pkgupload \
    --config-file configs/development/txpkgupload.yaml


echo "Done."
