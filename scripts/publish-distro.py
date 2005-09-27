#!/usr/bin/python

import logging

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger().debug("Publisher importing modules initialising...")

from canonical.lp import initZopeless
from canonical.archivepublisher import \
     DiskPool, Poolifier, POOL_DEBIAN, Config, Publisher, Dominator
import sys, os

from canonical.launchpad.database import (
    Distribution, DistroRelease, SourcePackagePublishingView,
    BinaryPackagePublishingView, SourcePackageFilePublishing,
    BinaryPackageFilePublishing)

from sqlobject import AND

from canonical.lp.dbschema import \
     PackagePublishingStatus, PackagePublishingPocket

from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import sqlvalues, SQLBase

# We do this for more accurate exceptions. It doesn't slow us down very
# much so it's not worth making it an option.
SQLBase._lazyUpdate = False

careful = False
if sys.argv[1] == "--careful":
    careful = True
    # XXX: dsilvers: 20050921: Replace all this with an option parser
    # but for now, and just for SteveA:
    # "lookee here, altering sys.argv"
    sys.argv.remove(1)
    

distroname = sys.argv[1]


error = logging.getLogger().error
warn = logging.getLogger().warn
info = logging.getLogger().info
debug = logging.getLogger().debug

info("Beginning publication process for %s" % distroname)

debug("Initialising zopeless...")

txn = initZopeless( dbuser='lucille' ) # Change this when we fix up db security

debug("Finding distribution and distrorelease objects...")

distro = Distribution.byName(distroname)
drs = DistroRelease.selectBy(distributionID=distro.id)

debug("Finding configuration...")

pubconf = Config(distro, drs)

debug("Making directories as needed...")

dirs = [
    pubconf.distroroot,
    pubconf.poolroot,
    pubconf.distsroot,
    pubconf.archiveroot,
    pubconf.cacheroot,
    pubconf.overrideroot,
    pubconf.miscroot
    ]

for d in dirs:
    if not os.path.exists(d):
        os.makedirs(d)


debug("Preparing on-disk pool representation...")

dp = DiskPool(Poolifier(POOL_DEBIAN),
              pubconf.poolroot, logging.getLogger("DiskPool"))
# Set the diskpool's log level to INFO to suppress debug output
dp.logger.setLevel(20)
dp.scan()

debug("Preparing publisher...")

pub = Publisher(logging.getLogger("Publisher"), pubconf, dp)

try:
    # main publishing section
    debug("Attempting to publish pending sources...")
    clause = "distribution = %s" % sqlvalues(distro.id)
    if not careful:
        clause = clause + (" AND publishingstatus = %s" %
                           sqlvalues(PackagePublishingStatus.PENDING))
    spps = SourcePackageFilePublishing.select(clause)
    pub.publish(spps, isSource=True)
    debug("Attempting to publish pending binaries...")
    pps = BinaryPackageFilePublishing.select(clause)
    pub.publish(pps, isSource=False)
        
except:
    logging.getLogger().exception("Bad muju while publishing")
    txn.abort()
    sys.exit(1)

judgejudy = Dominator(logging.getLogger("Dominator"))

try:
    debug("Attempting to perform domination...")
    for distrorelease in drs:
        for pocket in PackagePublishingPocket.items:
            judgejudy.judgeAndDominate(distrorelease, pocket, pubconf)
except:
    logging.getLogger().exception("Bad muju while dominating")
    txn.abort()
    sys.exit(1)

try:
    # Now we generate overrides
    debug("Generating overrides for the distro...")
    spps = SourcePackagePublishingView.select(
        AND(SourcePackagePublishingView.q.distribution == distro.id,
            SourcePackagePublishingView.q.publishingstatus == 
                PackagePublishingStatus.PUBLISHED ))
    pps = BinaryPackagePublishingView.select(
        AND(BinaryPackagePublishingView.q.distribution == distro.id,
            BinaryPackagePublishingView.q.publishingstatus == 
                PackagePublishingStatus.PUBLISHED ))

    pub.publishOverrides(spps, pps)
except:
    logging.getLogger().exception("Bad muju while generating overrides")
    txn.abort()
    sys.exit(1)

try:
    # Now we generate lists
    debug("Generating file lists...")
    spps = SourcePackageFilePublishing.select(
        AND(SourcePackageFilePublishing.q.distribution == distro.id,
            SourcePackageFilePublishing.q.publishingstatus ==
            PackagePublishingStatus.PUBLISHED ))
    pps = BinaryPackageFilePublishing.select(
        AND(BinaryPackageFilePublishing.q.distribution == distro.id,
            BinaryPackageFilePublishing.q.publishingstatus ==
                PackagePublishingStatus.PUBLISHED ))

    pub.publishFileLists(spps, pps)
except:
    logging.getLogger().exception("Bad muju while generating file lists")
    txn.abort()
    sys.exit(1)

try:
    # Generate apt-ftparchive config and run...
    debug("Doing apt-ftparchive work...")
    fn = os.tmpnam()
    f = file(fn,"w")
    f.write(pub.generateAptFTPConfig())
    f.close()
    print fn

    if os.system("apt-ftparchive generate "+fn) != 0:
        raise OSError("Unable to run apt-ftparchive properly")

except:
    logging.getLogger().exception("Bad muju while doing apt-ftparchive work")
    txn.abort()
    sys.exit(1)

try:
    # Generate the Release files...
    debug("Generating Release files...")
    pub.writeReleaseFiles(distro)
    
except:
    logging.getLogger().exception("Bad muju while doing release files")
    txn.abort()
    sys.exit(1)

try:
    # Unpublish death row
    debug("Unpublishing death row...")

    consrc = SourcePackageFilePublishing.select("""
        publishingstatus = %s AND
        sourcepackagepublishing.id =
                      sourcepackagefilepublishing.sourcepackagepublishing AND
        sourcepackagepublishing.scheduleddeletiondate <= %s
        """ % sqlvalues(PackagePublishingStatus.PENDINGREMOVAL, UTC_NOW),
                            clauseTables=['sourcepackagepublishing'])

    conbin = BinaryPackageFilePublishing.select("""
        publishingstatus = %s AND
        binarypackagepublishing.id =
                      binarypackagefilepublishing.binarypackagepublishing AND
        binarypackagepublishing.scheduleddeletiondate <= %s
        """ % sqlvalues(PackagePublishingStatus.PENDINGREMOVAL, UTC_NOW),
                            clauseTables=['binarypackagepublishing'])

    livesrc = SourcePackageFilePublishing.select(
        SourcePackageFilePublishing.q.publishingstatus != 
            PackagePublishingStatus.PENDINGREMOVAL)
    livebin = BinaryPackageFilePublishing.select(
        BinaryPackageFilePublishing.q.publishingstatus != 
            PackagePublishingStatus.PENDINGREMOVAL)
    
    pub.unpublishDeathRow(consrc, conbin, livesrc, livebin)

except:
    logging.getLogger().exception("Bad muju while doing death-row unpublish")
    txn.abort()
    sys.exit(1)

txn.commit()
