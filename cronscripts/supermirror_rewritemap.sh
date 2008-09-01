#!/bin/sh

set -e

RSYNC_FILE=/srv/launchpad.net/etc/supermirror_rewritemap.conf
PYTHON_VERSION=2.4
PYTHON=/usr/bin/python${PYTHON_VERSION}

if [ -f "$RSYNC_FILE" ]
then
    # Because we don't want to put the rsync password in a revision controlled
    # file, we store it in a configuration file.  By sourcing the configuration
    # file here, this makes it available for use by this script.
    . $RSYNC_FILE
else
    echo `date` "Supermirror config file not found, exiting"
    exit 1
fi

cd  /srv/launchpad.net/production/launchpad/cronscripts

LOCK=/var/lock/smrewrite.lock
MAP=/srv/launchpad.net/var/new-sm-map

lockfile -30 -r 3 ${LOCK}

$PYTHON supermirror_rewritemap.py -q ${MAP} && rsync ${MAP} \
        launchpad@bazaar.launchpad.net::config/launchpad-lookup.txt

rm -f ${LOCK}
