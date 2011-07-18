# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Publisher script class."""

__all__ = [
    'PublishDistro',
    ]

from optparse import OptionValueError
from zope.component import getUtility

from lp.app.errors import NotFoundError
from lp.archivepublisher.publishing import getPublisher
from lp.registry.interfaces.distribution import IDistributionSet
from lp.services.scripts.base import (
    LaunchpadCronScript,
    LaunchpadScriptFailure,
    )
from lp.soyuz.enums import (
    ArchivePurpose,
    ArchiveStatus,
    )
from lp.soyuz.interfaces.archive import (
    IArchiveSet,
    MAIN_ARCHIVE_PURPOSES,
    )


class PublishDistro(LaunchpadCronScript):
    """Distro publisher."""

    def add_my_options(self):
        self.parser.add_option(
            "-C", "--careful", action="store_true", dest="careful",
            default=False, help="Turns on all the below careful options.")

        self.parser.add_option(
            "-P", "--careful-publishing", action="store_true",
            dest="careful_publishing", default=False,
            help="Make the package publishing process careful.")

        self.parser.add_option(
            "-D", "--careful-domination", action="store_true",
            dest="careful_domination", default=False,
            help="Make the domination process careful.")

        self.parser.add_option(
            "-A", "--careful-apt", action="store_true", dest="careful_apt",
            default=False,
            help="Make index generation (e.g. apt-ftparchive) careful.")

        self.parser.add_option(
            "-d", "--distribution", dest="distribution", metavar="DISTRO",
            default="ubuntu", help="The distribution to publish.")

        self.parser.add_option(
            '-s', '--suite', metavar='SUITE', dest='suite', action='append',
            type='string', default=[], help='The suite to publish')

        self.parser.add_option(
            "-R", "--distsroot", dest="distsroot", metavar="SUFFIX",
            default=None,
            help=(
                "Override the dists path for generation of the PRIMARY and "
                "PARTNER archives only."))

        self.parser.add_option(
            "--ppa", action="store_true", dest="ppa", default=False,
            help="Only run over PPA archives.")

        self.parser.add_option(
            "--private-ppa", action="store_true", dest="private_ppa",
            default=False, help="Only run over private PPA archives.")

        self.parser.add_option(
            "--partner", action="store_true", dest="partner", default=False,
            help="Only run over the partner archive.")

        self.parser.add_option(
            "--copy-archive", action="store_true", dest="copy_archive",
            default=False, help="Only run over the copy archives.")

        self.parser.add_option(
            "--primary-debug", action="store_true", default=False,
            dest="primary_debug",
            help="Only run over the debug-symbols for primary archive.")

    def logOption(self, description, option):
        """Describe the state of `option` to the debug log."""
        if self.options.careful:
            care = "Careful (Overridden)"
        elif option:
            care = "Careful"
        else:
            care = "Normal"
        self.logger.debug("%14s: %s", description, care)

    def countExclusiveOptions(self):
        """Return the number of exclusive "mode" options that were set.

        In valid use, at most one of them should be set.
        """
        exclusive_options = [
            self.options.partner,
            self.options.ppa,
            self.options.private_ppa,
            self.options.primary_debug,
            self.options.copy_archive,
            ]
        return len(filter(None, exclusive_options))

    def logOptions(self):
        """Dump the selected options to the debug log."""
        if self.countExclusiveOptions() == 0:
            indexing_engine = "Apt-FTPArchive"
        else:
            indexing_engine = "Indexing"
        log_items = [
            ('Distribution', self.options.distribution),
            ('Publishing', self.options.careful_publishing),
            ('Domination', self.options.careful_domination),
            (indexing_engine, self.options.careful_apt),
            ]
        for description, option in log_items:
            self.logOption(description, option)

    def validateOptions(self):
        """Check given options for user interface violations."""
        if len(self.args) > 0:
            raise OptionValueError(
                "publish-distro takes no arguments, only options.")
        if self.countExclusiveOptions() > 1:
            raise OptionValueError(
                "Can only specify one of partner, ppa, private-ppa, "
                "copy-archive and primary-debug.")

        for_ppa = (self.options.ppa or self.options.private_ppa)
        if for_ppa and self.options.distsroot:
            raise OptionValueError(
                "We should not define 'distsroot' in PPA mode!", )

    def findDistro(self):
        """Find the selected distribution."""
        self.logger.debug("Finding distribution object.")
        try:
            return getUtility(IDistributionSet).getByName(
                self.options.distribution)
        except NotFoundError, e:
            raise OptionValueError(e)

    def findSuite(self, distribution, suite):
        """Find the named `suite` in `distribution`."""
        try:
            return distribution.getDistroSeriesAndPocket(suite)
        except NotFoundError, e:
            raise OptionValueError(e)

    def findAllowedSuites(self, distribution):
        """Find the selected suite(s)."""
        return set([
            self.findSuite(distribution, suite)
            for suite in self.options.suite])

    def findDebugArchive(self, distribution):
        """Find the debug archive for `distribution`."""
        debug_archive = getUtility(IArchiveSet).getByDistroPurpose(
            distribution, ArchivePurpose.DEBUG)
        if debug_archive is None:
            raise OptionValueError(
                "Could not find DEBUG archive for %s" % distribution.name)
        return debug_archive

    def getCopyArchives(self, distribution):
        """Find copy archives for `distribution`, if any."""
        copy_archives = list(
            getUtility(IArchiveSet).getArchivesForDistribution(
                distribution, purposes=[ArchivePurpose.COPY]))
        if copy_archives == []:
            raise LaunchpadScriptFailure("Could not find any COPY archives")
        return copy_archives

    def getPPAs(self, distribution):
        """Find private package archive(s) for `distribution`."""
        if self.options.careful or self.options.careful_publishing:
            return distribution.getAllPPAs()
        else:
            return distribution.getPendingPublicationPPAs()

    def hasDesiredPrivacy(self, ppa):
        """Does `ppa` have the privacy setting we're looking for?

        Picks out private archives if we're publishing private PPAs only,
        or public ones if we're doing non-private.
        """
        return bool(ppa.private) == bool(self.options.private_ppa)

    def getTargetArchives(self, distribution):
        """Find the archive(s) selected by the script's options."""
        if self.options.partner:
            return [distribution.getArchiveByComponent('partner')]
        elif self.options.ppa or self.options.private_ppa:
            return filter(self.hasDesiredPrivacy, self.getPPAs(distribution))
        elif self.options.primary_debug:
            return [self.findDebugArchive(distribution)]
        elif self.options.copy_archive:
            return self.getCopyArchives(distribution)
        else:
            return [distribution.main_archive]

    def isActiveArchive(self, archive):
        """Is this an archive we're supposed to act on?

        Considers only archives that have their "to be published" flag
        turned on, or are pending deletion.
        """
        return archive.publish or (archive.status == ArchiveStatus.DELETING)

    def getPublisher(self, distribution, archive, allowed_suites):
        """Get a publisher for the given options."""
        if archive.purpose in MAIN_ARCHIVE_PURPOSES:
            description = "%s %s" % (distribution.name, archive.displayname)
            # Only let the primary/partner archives override the distsroot.
            distsroot = self.options.distsroot
        else:
            description = archive.archive_url
            distsroot = None

        self.logger.info("Processing %s", description)
        return getPublisher(archive, allowed_suites, self.logger, distsroot)

    def deleteArchive(self, archive, publisher):
        """Ask `publisher` to delete `archive`."""
        if archive.purpose == ArchivePurpose.PPA:
            publisher.deleteArchive()
            self.txn.commit()
        else:
            # Other types of archives do not currently support deletion.
            self.logger.warning(
                "Deletion of %s skipped: operation not supported on %s",
                archive.displayname, archive.purpose.title)

    def publishArchive(self, archive, publisher):
        """Ask `publisher` to publish `archive`."""
        publisher.A_publish(
            self.options.careful or self.options.careful_publishing)
        self.txn.commit()

        # Flag dirty pockets for any outstanding deletions.
        publisher.A2_markPocketsWithDeletionsDirty()
        publisher.B_dominate(
            self.options.careful or self.options.careful_domination)
        self.txn.commit()

        # The primary and copy archives use apt-ftparchive to
        # generate the indexes, everything else uses the newer
        # internal LP code.
        if archive.purpose in (ArchivePurpose.PRIMARY, ArchivePurpose.COPY):
            publisher.C_doFTPArchive(
                self.options.careful or self.options.careful_apt)
        else:
            publisher.C_writeIndexes(
                self.options.careful or self.options.careful_apt)
        self.txn.commit()

        publisher.D_writeReleaseFiles(
            self.options.careful or self.options.careful_apt)
        self.txn.commit()

    def main(self):
        """See `LaunchpadScript`."""
        self.validateOptions()
        self.logOptions()
        distribution = self.findDistro()
        allowed_suites = self.findAllowedSuites(distribution)
        archives = filter(
            self.isActiveArchive, self.getTargetArchives(distribution))

        for archive in archives:
            publisher = self.getPublisher(
                distribution, archive, allowed_suites)

            if archive.status == ArchiveStatus.DELETING:
                self.deleteArchive(archive, publisher)
            else:
                self.publishArchive(archive, publisher)

        self.logger.debug("Ciao")
