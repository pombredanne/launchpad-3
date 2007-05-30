#!/bin/sh

# This script performs nightly chores. It should be run from 
# cron as the launchpad user once a day. Typically the output
# will be sent to an email address for inspection.

export LPCONFIG=lpnet1
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

echo == Updating bug watches `date` ==
python checkwatches.py

echo == Product Release Finder `date` ==
python product-release-finder.py -q

echo '== Distribution mirror prober (archive)' `date` ==
# Force because we know we are only running this once a day
python distributionmirror-prober.py --content-type=archive --force --no-owner-notification

echo '== Distribution mirror prober (release)' `date` ==
# Force beause we know we are only running this once a day
python distributionmirror-prober.py --content-type=release --force --no-owner-notification


rm -f $LOCK

