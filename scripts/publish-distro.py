#!/usr/bin/python

import logging

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger().debug("Publisher importing modules initialising...")

from canonical.lp import initZopeless
from canonical.archivepublisher import \
     DiskPool, Poolifier, POOL_DEBIAN, Config, Publisher, Dominator
import sys, os
from canonical.launchpad.database import \
     Distribution, DistroRelease, SourcePackagePublishingView, \
     BinaryPackagePublishingView, SourcePackageFilePublishing, \
     BinaryPackageFilePublishing

from sqlobject import AND

from canonical.lp.dbschema import \
     PackagePublishingStatus, PackagePublishingPocket

from canonical.database.constants import UTC_NOW

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

c = Config(distro, drs)

debug("Making directories as needed...")

dirs = [
    c.distroroot,
    c.poolroot,
    c.distsroot,
    c.archiveroot,
    c.cacheroot,
    c.overrideroot,
    c.miscroot
    ]

for d in dirs:
    if not os.path.exists(d):
        os.makedirs(d)


debug("Preparing on-disk pool representation...")

dp = DiskPool(Poolifier(POOL_DEBIAN),
              c.poolroot, logging.getLogger("DiskPool"))

dp.scan()

debug("Preparing publisher...")

pub = Publisher(logging.getLogger("Publisher"), c, dp)

try:
    # main publishing section
    debug("Attempting to publish pending sources...")
    spps = SourcePackageFilePublishing.selectBy(
        distribution = distro.id )
    pub.publish(spps, isSource=True)
    debug("Attempting to publish pending binaries...")
    pps = BinaryPackageFilePublishing.selectBy(
        distribution = distro.id )
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
            judgejudy.judgeAndDominate(distrorelease,pocket)            
except:
    logging.getLogger().exception("Bad muju while dominating")
    txn.abort()
    sys.exit(1)

try:
    # Now we generate overrides
    debug("Generating overrides for the distro...")
    spps = SourcePackagePublishingView.select(
        AND(SourcePackagePublishingView.q.distribution == distro.id,
        SourcePackagePublishingView.q.publishingstatus != PackagePublishingStatus.PENDINGREMOVAL ))
    pps = BinaryPackagePublishingView.select(
        AND(BinaryPackagePublishingView.q.distribution == distro.id,
        BinaryPackagePublishingView.q.publishingstatus != PackagePublishingStatus.PENDINGREMOVAL ))

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
        SourcePackageFilePublishing.q.publishingstatus != PackagePublishingStatus.PENDINGREMOVAL ))
    pps = BinaryPackageFilePublishing.select(
        AND(BinaryPackageFilePublishing.q.distribution == distro.id,
        BinaryPackageFilePublishing.q.publishingstatus != PackagePublishingStatus.PENDINGREMOVAL ))

    pub.publishFileLists(spps,pps)
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
    # Unpublish death row
    debug("Unpublishing death row...")
    consrc = SourcePackagePublishing.select(
        AND(SourcePackagePublishing.q.status == PackagePublishingStatus.PENDINGREMOVAL,
            SourcePackagePublishing.q.scheduleddeletiondate <= UTC_NOW))
    conbin = PackagePublishing.select(
        AND(PackagePublishing.q.status == PackagePublishingStatus.PENDINGREMOVAL,
            PackagePublishing.q.scheduleddeletiondate <= UTC_NOW))
    
    livesrc = SourcePackagePublishing.select(
        SourcePackagePublishing.q.status != PackagePublishingStatus.PENDINGREMOVAL)
    livebin = PackagePublishing.select(
        PackagePublishing.q.status != PackagePublishingStatus.PENDINGREMOVAL)
    
    pub.unpublishDeathRow(consrc, conbin, livesrc, livebin)

except:
    logging.getLogger().exception("Bad muju while doing death-row unpublish")
    txn.abort()
    sys.exit(1)

txn.commit()
