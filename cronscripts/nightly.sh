#!/bin/sh
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# This script performs nightly chores. It should be run from 
# cron as the launchpad user once a day. Typically the output
# will be sent to an email address for inspection.

# Note that http/ftp proxies are needed by the product 
# release finder

# Only run this script on loganberry
THISHOST=`uname -n`
if [ "loganberry" != "$THISHOST" ]
then
        echo "This script must be run on loganberry."
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

echo == Allocating revision karma `date` ==
python allocate-revision-karma.py -q

echo == Recalculating karma `date` ==
python foaf-update-karma-cache.py -q

echo == Updating cached statistics `date` ==
python update-stats.py -q

echo == Expiring questions `date` ==
python expire-questions.py

### echo == Expiring bugs `date` ==
### python expire-bugtasks.py

# checkwatches.py is scheduled in the /code/pqm/launchpad_crontabs branch.
### echo == Updating bug watches `date` ==
### python checkwatches.py

echo == Updating bugtask target name caches `date` ==
python update-bugtask-targetnamecaches.py -q

echo == Updating personal standings `date` ==
python update-standing.py -q

echo == Updating CVE database `date` ==
python update-cve.py -q

echo == Updating package cache `date` ==
python update-pkgcache.py -q

echo == Product Release Finder `date` ==
python product-release-finder.py -q


rm -f $LOCK
