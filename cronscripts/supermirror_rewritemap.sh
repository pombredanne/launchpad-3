#!/bin/sh

RSYNC_FILE=/srv/launchpad.net/etc/supermirror_rewritemap.conf

if [ -f "$RSYNC_FILE" ]
then
    . $RSYNC_FILE
else
    echo `date` "Supermirror config file not found, exiting"
    exit 1
fi

cd  /srv/launchpad.net/production/launchpad/cronscripts

LOCK=/var/lock/smrewrite.lock
MAP=/tmp/new-sm-map

lockfile -l 600 ${LOCK}

python supermirror_rewritemap.py -q /tmp/new-sm-map && rsync ${MAP} \
        launchpad@bazaar.launchpad.net::config/launchpad-lookup.txt

rm -f ${LOCK}
