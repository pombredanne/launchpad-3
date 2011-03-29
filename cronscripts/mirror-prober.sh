#!/bin/sh
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# This script runs the mirror prober scripts as the
# launchpad user every two hours. Typically the output
# will be sent to an email address for inspection.

# Only run this script on loganberry
THISHOST=$(uname -n)
if [ "loganberry" != "$THISHOST" ]
then
        echo "This script must be run on loganberry."
        exit 1
fi

# Only run this as the launchpad user
USER=$(whoami)
if [ "launchpad" != "$USER" ]
then
        echo "Must be launchpad user to run this script."
        exit 1
fi


export LPCONFIG=distromirror
export http_proxy=http://squid.internal:3128/
export ftp_proxy=http://squid.internal:3128/

LOGFILE=/srv/launchpad.net/production-logs/mirror-prober.log

LOCK=/var/lock/launchpad_mirror_prober.lock
lockfile -r0 -l 259200 $LOCK
if [ $? -ne 0 ]; then
    echo $(date): Unable to grab $LOCK lock - aborting | tee -a $LOGFILE
    ps fuxwww
    exit 1
fi

cd /srv/launchpad.net/production/launchpad/cronscripts

echo $(date): Grabbed lock >> $LOGFILE

echo $(date): Probing archive mirrors >> $LOGFILE
python -S distributionmirror-prober.py -q --content-type=archive --max-mirrors=20 --log-file=DEBUG:$LOGFILE

echo $(date): Probing cdimage mirrors >> $LOGFILE
python -S distributionmirror-prober.py -q --content-type=cdimage --max-mirrors=30 --log-file=DEBUG:$LOGFILE

echo $(date): Removing lock >> $LOGFILE
rm -f $LOCK

