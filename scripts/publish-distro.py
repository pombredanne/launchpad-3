#!/usr/bin/python

import logging
import gc

import _pythonpath

from optparse import OptionParser
from canonical.config import config
from canonical.launchpad.scripts import (execute_zcml_for_scripts,
                                         logger, logger_options)

from canonical.lp import initZopeless
from canonical.archivepublisher import (
    DiskPool, Poolifier, POOL_DEBIAN, Config, Publisher, Dominator,
    LucilleConfigError)
import sys, os

from canonical.launchpad.database import (
    Distribution, DistroRelease, SourcePackagePublishingView,
    BinaryPackagePublishingView, SourcePackageFilePublishing,
    BinaryPackageFilePublishing, SecureSourcePackagePublishingHistory,
    SecureBinaryPackagePublishingHistory)

from sqlobject import AND

from canonical.lp.dbschema import (
     PackagePublishingStatus, PackagePublishingPocket,
     DistributionReleaseStatus)

from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import (
    sqlvalues, SQLBase, flush_database_updates,
    clear_current_connection_cache)

# These states are used for domination unless we're being careful
non_careful_domination_states = set([
    DistributionReleaseStatus.EXPERIMENTAL,
    DistributionReleaseStatus.DEVELOPMENT,
    DistributionReleaseStatus.FROZEN])

# We do this for more accurate exceptions. It doesn't slow us down very
# much so it's not worth making it an option.
SQLBase._lazyUpdate = False

def clear_cache():
    """Flush SQLObject updates and clear the cache."""
    # Flush them anyway, should basically be a noop thanks to not doing
    # lazyUpdate.
    flush_database_updates()
    clear_current_connection_cache()
    gc.collect()


parser = OptionParser()
logger_options(parser)

parser.add_option("-C", "--careful", action="store_true",
                  dest="careful", metavar="", default=False,
                  help="Turns on all the below careful options.")

parser.add_option("-P", "--careful-publishing", action="store_true",
                  dest="careful_publishing", metavar="", default=False,
                  help="Make the package publishing process careful.")

parser.add_option("-D", "--careful-domination", action="store_true",
                  dest="careful_domination", metavar="", default=False,
                  help="Make the domination process careful.")

parser.add_option("-A", "--careful-apt", action="store_true",
                  dest="careful_apt", metavar="", default=False,
                  help="Make the apt-ftparchive run careful.")

parser.add_option("-d", "--distribution",
                  dest="distribution", metavar="DISTRO", default="ubuntu",
                  help="The distribution to publish.")

parser.add_option("-R", "--distsroot",
                  dest="distsroot", metavar="SUFFIX", default=None,
                  help="Override the dists path for generation")

(options, args) = parser.parse_args()

log = logger(options, "process-upload")

distroname = options.distribution

assert len(args) == 0, "publish-distro takes no arguments, only options."

error = log.error
warn = log.warn
info = log.info
debug = log.debug

def careful_msg(what):
    """Quick handy util for the below."""
    if options.careful:
        return "Careful (Overridden)"
    if what:
        return "Careful"
    return "Normal"

info("  Distribution: %s" % distroname)
info("    Publishing: %s" % careful_msg(options.careful_publishing))
info("    Domination: %s" % careful_msg(options.careful_domination))
info("Apt-FTPArchive: %s" % careful_msg(options.careful_apt))


debug("Initialising zopeless.")

txn = initZopeless(dbuser='lucille') # Change this when we fix up db security
execute_zcml_for_scripts()

debug("Finding distribution and distrorelease objects.")

distro = Distribution.byName(distroname)
drs = DistroRelease.selectBy(distributionID=distro.id)

debug("Finding configuration.")

try:
    pubconf = Config(distro, drs)
except LucilleConfigError, info:
    error(info)
    sys.exit(1)

if options.distsroot is not None:
    pubconf.distsroot = options.distsroot

debug("Making directories as needed.")

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


debug("Preparing on-disk pool representation.")

dp = DiskPool(Poolifier(POOL_DEBIAN),
              pubconf.poolroot, logging.getLogger("DiskPool"))
# Set the diskpool's log level to INFO to suppress debug output
dp.logger.setLevel(20)
dp.scan()

debug("Preparing publisher.")

#pub = Publisher(logging.getLogger("Publisher"), pubconf, dp, distro)
pub = Publisher(log, pubconf, dp, distro)

try:
    # main publishing section
    debug("Attempting to publish pending sources.")
    clause = "distribution = %s" % sqlvalues(distro.id)
    if not (options.careful or options.careful_publishing):
        clause = clause + (" AND publishingstatus = %s" %
                           sqlvalues(PackagePublishingStatus.PENDING))
    spps = SourcePackageFilePublishing.select(clause, orderBy=['componentname', 'sourcepackagename', 'libraryfilealiasfilename'])
    pub.publish(spps, isSource=True)
    debug("Flushing caches.")
    clear_cache()
    debug("Attempting to publish pending binaries.")
    pps = BinaryPackageFilePublishing.select(clause, orderBy=['componentname', 'sourcepackagename', 'libraryfilealiasfilename'])
    pub.publish(pps, isSource=False)
    debug("Committing.")
    txn.commit()
    debug("Flushing caches.")
    clear_cache()
except:
    logging.getLogger().exception("Bad muju while publishing")
    txn.abort()
    sys.exit(1)

judgejudy = Dominator(logging.getLogger("Dominator"))

is_careful_domination = options.careful or options.careful_domination
try:
    debug("Attempting to perform domination.")
    for distrorelease in drs:
        for pocket in PackagePublishingPocket.items:
            is_in_development = (distrorelease.releasestatus in
                                non_careful_domination_states)
            is_release_pocket = pocket == PackagePublishingPocket.RELEASE
            if (is_careful_domination or is_in_development or
                not is_release_pocket):
                debug("Domination for %s (%s)" % (
                    distrorelease.name, pocket.name))
                judgejudy.judgeAndDominate(distrorelease, pocket, pubconf)
                debug("Flushing caches.")
                clear_cache()
            debug("Committing.")
            txn.commit()
except:
    logging.getLogger().exception("Bad muju while dominating")
    txn.abort()
    sys.exit(1)

try:
    debug("Preparing file lists and overrides.")
    pub.createEmptyPocketRequests()
except:
    logging.getLogger().exception("Bad muju while preparing file lists etc.")
    txn.abort()
    sys.exit(1)

try:
    # Now we generate overrides
    debug("Generating overrides for the distro.")
    spps = SourcePackagePublishingView.select(
        AND(SourcePackagePublishingView.q.distribution == distro.id,
            SourcePackagePublishingView.q.publishingstatus == 
                PackagePublishingStatus.PUBLISHED ))
    pps = BinaryPackagePublishingView.select(
        AND(BinaryPackagePublishingView.q.distribution == distro.id,
            BinaryPackagePublishingView.q.publishingstatus == 
                PackagePublishingStatus.PUBLISHED ))

    pub.publishOverrides(spps, pps)
    debug("Flushing caches.")
    clear_cache()
except:
    logging.getLogger().exception("Bad muju while generating overrides")
    txn.abort()
    sys.exit(1)

try:
    # Now we generate lists
    debug("Generating file lists.")
    spps = SourcePackageFilePublishing.select(
        AND(SourcePackageFilePublishing.q.distribution == distro.id,
            SourcePackageFilePublishing.q.publishingstatus ==
            PackagePublishingStatus.PUBLISHED ))
    pps = BinaryPackageFilePublishing.select(
        AND(BinaryPackageFilePublishing.q.distribution == distro.id,
            BinaryPackageFilePublishing.q.publishingstatus ==
                PackagePublishingStatus.PUBLISHED ))

    pub.publishFileLists(spps, pps)
    debug("Committing.")
    txn.commit()
    debug("Flushing caches.")
    clear_cache()
except:
    logging.getLogger().exception("Bad muju while generating file lists")
    txn.abort()
    sys.exit(1)

try:
    # Generate apt-ftparchive config and run.
    debug("Doing apt-ftparchive work.")
    # fn = os.tmpnam()
    fn = os.path.join(pubconf.miscroot, "apt.conf")
    f = file(fn, "w")
    f.write(pub.generateAptFTPConfig(fullpublish=(
        options.careful or options.careful_apt)))
    f.close()
    print fn

    if os.system("apt-ftparchive --no-contents generate "+fn) != 0:
        raise OSError("Unable to run apt-ftparchive properly")

except:
    logging.getLogger().exception("Bad muju while doing apt-ftparchive work")
    txn.abort()
    sys.exit(1)

try:
    # Generate the Release files.
    debug("Generating Release files.")
    pub.writeReleaseFiles(full_run=(options.careful or options.careful_apt))
    
except:
    logging.getLogger().exception("Bad muju while doing release files")
    txn.abort()
    sys.exit(1)

try:
    # Unpublish death row
    debug("Unpublishing death row.")

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

    # Now that the os.remove() calls have been made, simply let every
    # now out-of-date record be marked as removed.

    debug("Marking condemned sources as removed.")
    consrc = SecureSourcePackagePublishingHistory.select(
        "status = %s AND scheduleddeletiondate <= %s" % sqlvalues(
        PackagePublishingStatus.PENDINGREMOVAL, UTC_NOW))
    for pubrec in consrc:
        pubrec.status = PackagePublishingStatus.REMOVED
        pubrec.dateremoved = UTC_NOW
        
    debug("Marking condemned binaries as removed.")
    conbin = SecureBinaryPackagePublishingHistory.select(
        "status = %s AND scheduleddeletiondate <= %s" % sqlvalues(
        PackagePublishingStatus.PENDINGREMOVAL, UTC_NOW))
    for pubrec in conbin:
        pubrec.status = PackagePublishingStatus.REMOVED
        pubrec.dateremoved = UTC_NOW

    debug("Committing")
    txn.commit()

except:
    logging.getLogger().exception("Bad muju while doing death-row unpublish")
    txn.abort()
    sys.exit(1)

try:
    debug("Sanitising links in the pool.")
    dp.sanitiseLinks(['main', 'restricted', 'universe', 'multiverse'])
except:
    logging.getLogger().exception("Bad muju while sanitising links.")
    sys.exit(1)

debug("All done, committing anything left over before bed.")

txn.commit()

debug("Ciao")
