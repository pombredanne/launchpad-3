#!/bin/sh

RSYNC_FILE=/srv/staging.launchpad.net/etc/supermirror_rewritemap.conf
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

# We want to override any value that's been set so that
# when this script is run it always uses LPCONFIG=staging
export LPCONFIG=staging

cd  /srv/staging.launchpad.net/staging/launchpad/cronscripts

LOCK=/var/lock/smrewrite.lock
MAP=/srv/staging.launchpad.net/var/new-sm-map

lockfile -l 600 ${LOCK}

$PYTHON supermirror_rewritemap.py -q ${MAP} && rsync ${MAP} \
        launchpad@bazaar.staging.launchpad.net::config/launchpad-lookup.txt

rm -f ${LOCK}
