#!/bin/sh

# This script performs nightly chores. It should be run from 
# cron as the launchpad user once a day. Typically the output
# will be sent to an email address for inspection.

# Note that http/ftp proxies are needed by the product 
# release finder

# Only run this script on forster
THISHOST=`uname -n`
if [ "forster" != "$THISHOST" ]
then
        echo "This script must be run on forster."
        exit 1
fi

# Only run this as the launchpad user
USER=`whoami`
if [ "launchpad" != "$USER" ]
then
        echo "Must be launchpad user to run this script."
        exit 1
fi


export LPCONFIG=production
export http_proxy=http://squid.internal:3128/
export ftp_proxy=http://squid.internal:3128/

LOCK=/var/lock/launchpad_nightly.lock
lockfile -r0 -l 259200 $LOCK
if [ $? -ne 0 ]; then
    echo Unable to grab $LOCK lock - aborting
    ps fuxwww
    exit 1
fi

cd /srv/launchpad.net/production/launchpad/cronscripts

echo == Expiring memberships `date` ==
python flag-expired-memberships.py -q

echo == Recalculating karma `date` ==
python foaf-update-karma-cache.py -q

echo == Updating cached statistics `date` ==
python update-stats.py -q

echo == Updating package cache `date` ==
python update-pkgcache.py -q

echo == Updating CVE database `date` ==
python update-cve.py -q

echo == Updating bugtask target name caches `date` ==
python update-bugtask-targetnamecaches.py -q

echo == Expiring questions `date` ==
python expire-questions.py

echo == Expiring bugs `date` ==
# XXX Do not enable expire-bugtasks until users have beta tested it.
#python expire-bugtasks.py

echo == Product Release Finder `date` ==
python product-release-finder.py -q

echo == Updating bug watches `date` ==
LPCONFIG=production LP_DBUSER=temp_checkwatches python checkwatches.py

rm -f $LOCK

