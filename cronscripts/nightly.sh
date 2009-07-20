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
python2.4 flag-expired-memberships.py -q

echo == Allocating revision karma `date` ==
python2.4 allocate-revision-karma.py -q

echo == Recalculating karma `date` ==
python2.4 foaf-update-karma-cache.py -q

echo == Updating cached statistics `date` ==
python2.4 update-stats.py -q

echo == Expiring questions `date` ==
python2.4 expire-questions.py

### echo == Expiring bugs `date` ==
### python2.4 expire-bugtasks.py

# checkwatches.py is scheduled in the /code/pqm/launchpad_crontabs branch.
### echo == Updating bug watches `date` ==
### python2.4 checkwatches.py

echo == Updating bugtask target name caches `date` ==
python2.4 update-bugtask-targetnamecaches.py -q

echo == Updating personal standings `date` ==
python2.4 update-standing.py -q

echo == Updating CVE database `date` ==
python2.4 update-cve.py -q

echo == Updating package cache `date` ==
python2.4 update-pkgcache.py -q

echo == POFile stats `date` ==
python2.4 rosetta-pofile-stats.py

echo == Product Release Finder `date` ==
python2.4 product-release-finder.py -q


rm -f $LOCK
