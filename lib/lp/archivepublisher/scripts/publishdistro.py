# Copyright 2009-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Publisher script class."""

__all__ = [
    'PublishDistro',
    ]

from optparse import OptionValueError

from zope.component import getUtility

from lp.app.errors import NotFoundError
from lp.archivepublisher.publishing import (
    cannot_modify_suite,
    getPublisher,
    GLOBAL_PUBLISHER_LOCK,
    )
from lp.archivepublisher.scripts.base import PublisherScript
from lp.services.scripts.base import LaunchpadScriptFailure
from lp.soyuz.enums import (
    ArchivePurpose,
    ArchiveStatus,
    )
from lp.soyuz.interfaces.archive import (
    IArchiveSet,
    MAIN_ARCHIVE_PURPOSES,
    )


def is_ppa_private(ppa):
    """Is `ppa` private?"""
    return ppa.private


def is_ppa_public(ppa):
    """Is `ppa` public?"""
    return not ppa.private


class PublishDistro(PublisherScript):
    """Distro publisher."""

    lockfilename = GLOBAL_PUBLISHER_LOCK

    def add_my_options(self):
        self.addDistroOptions()

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
            "--careful-release", action="store_true", dest="careful_release",
            default=False,
            help="Make the Release file generation process careful.")

        self.parser.add_option(
            "--disable-publishing", action="store_false",
            dest="enable_publishing", default=True,
            help="Disable the package publishing process.")

        self.parser.add_option(
            "--disable-domination", action="store_false",
            dest="enable_domination", default=True,
            help="Disable the domination process.")

        self.parser.add_option(
            "--disable-apt", action="store_false",
            dest="enable_apt", default=True,
            help="Disable index generation (e.g. apt-ftparchive).")

        self.parser.add_option(
            "--disable-release", action="store_false",
            dest="enable_release", default=True,
            help="Disable the Release file generation process.")

        self.parser.add_option(
            "--include-non-pending", action="store_true",
            dest="include_non_pending", default=False,
            help=(
                "When publishing PPAs, also include those that do not have "
                "pending publications."))

        self.parser.add_option(
            '-s', '--suite', metavar='SUITE', dest='suite', action='append',
            type='string', default=[], help='The suite to publish')

        self.parser.add_option(
            "--dirty-suite", metavar="SUITE", dest="dirty_suites",
            action="append", default=[],
            help="Consider this suite dirty regardless of publications.")

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

    def isCareful(self, option):
        """Is the given "carefulness" option enabled?

        Yes if the option is True, but also if the global "careful" option
        is set.

        :param option: The specific "careful" option to test, e.g.
            `self.options.careful_publishing`.
        :return: Whether the option should be treated as asking us to be
            careful.
        """
        return option or self.options.careful

    def describeCare(self, option):
        """Helper: describe carefulness setting of given option.

        Produces a human-readable string saying whether the option is set
        to careful mode; or "overridden" to careful mode by the global
        "careful" option; or is left in normal mode.
        """
        if self.options.careful:
            return "Careful (Overridden)"
        elif option:
            return "Careful"
        else:
            return "Normal"

    def logOption(self, name, value):
        """Describe the state of `option` to the debug log."""
        self.logger.debug("%14s: %s", name, value)

    def countExclusiveOptions(self):
        """Return the number of exclusive "mode" options that were set.

        In valid use, at most one of them should be set.
        """
        exclusive_options = [
            self.options.partner,
            self.options.ppa,
            self.options.private_ppa,
            self.options.copy_archive,
            ]
        return len(filter(None, exclusive_options))

    def logOptions(self):
        """Dump the selected options to the debug log."""
        if self.countExclusiveOptions() == 0:
            indexing_engine = "Apt-FTPArchive"
        else:
            indexing_engine = "Indexing"
        self.logOption('Distribution', self.options.distribution)
        log_items = [
            ('Publishing', self.options.careful_publishing),
            ('Domination', self.options.careful_domination),
            (indexing_engine, self.options.careful_apt),
            ('Release', self.options.careful_release),
            ]
        for name, option in log_items:
            self.logOption(name, self.describeCare(option))

    def validateOptions(self):
        """Check given options for user interface violations."""
        if len(self.args) > 0:
            raise OptionValueError(
                "publish-distro takes no arguments, only options.")
        if self.countExclusiveOptions() > 1:
            raise OptionValueError(
                "Can only specify one of partner, ppa, private-ppa, "
                "copy-archive.")

        if self.options.all_derived and self.options.distribution is not None:
                raise OptionValueError(
                    "Specify --distribution or --all-derived, but not both.")

        for_ppa = (self.options.ppa or self.options.private_ppa)
        if for_ppa and self.options.distsroot:
            raise OptionValueError(
                "We should not define 'distsroot' in PPA mode!", )

    def findSuite(self, distribution, suite):
        """Find the named `suite` in the selected `Distribution`.

        :param suite: The suite name to look for.
        :return: A tuple of distroseries and pocket.
        """
        try:
            series, pocket = distribution.getDistroSeriesAndPocket(suite)
        except NotFoundError as e:
            raise OptionValueError(e)
        return series, pocket

    def findAllowedSuites(self, distribution):
        """Find the selected suite(s)."""
        suites = set()
        for suite in self.options.suite:
            series, pocket = self.findSuite(distribution, suite)
            suites.add((series.name, pocket))
        return suites

    def getCopyArchives(self, distribution):
        """Find copy archives for the selected distribution."""
        copy_archives = list(
            getUtility(IArchiveSet).getArchivesForDistribution(
                distribution, purposes=[ArchivePurpose.COPY]))
        if copy_archives == []:
            raise LaunchpadScriptFailure("Could not find any COPY archives")
        return copy_archives

    def getPPAs(self, distribution):
        """Find private package archives for the selected distribution."""
        if (self.isCareful(self.options.careful_publishing) or
                self.options.include_non_pending):
            return distribution.getAllPPAs()
        else:
            return distribution.getPendingPublicationPPAs()

    def getTargetArchives(self, distribution):
        """Find the archive(s) selected by the script's options."""
        if self.options.partner:
            return [distribution.getArchiveByComponent('partner')]
        elif self.options.ppa:
            return filter(is_ppa_public, self.getPPAs(distribution))
        elif self.options.private_ppa:
            return filter(is_ppa_private, self.getPPAs(distribution))
        elif self.options.copy_archive:
            return self.getCopyArchives(distribution)
        else:
            return [distribution.main_archive]

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
            return True
        else:
            # Other types of archives do not currently support deletion.
            self.logger.warning(
                "Deletion of %s skipped: operation not supported on %s",
                archive.displayname, archive.purpose.title)
            return False

    def publishArchive(self, archive, publisher):
        """Ask `publisher` to publish `archive`.

        Commits transactions along the way.
        """
        publisher.setupArchiveDirs()
        if self.options.enable_publishing:
            publisher.A_publish(
                self.isCareful(self.options.careful_publishing))
            self.txn.commit()

        if self.options.enable_domination:
            # Flag dirty pockets for any outstanding deletions.
            publisher.A2_markPocketsWithDeletionsDirty()
            publisher.B_dominate(
                self.isCareful(self.options.careful_domination))
            self.txn.commit()

        if self.options.enable_apt:
            # The primary and copy archives use apt-ftparchive to
            # generate the indexes, everything else uses the newer
            # internal LP code.
            careful_indexing = self.isCareful(self.options.careful_apt)
            if archive.purpose in (
                    ArchivePurpose.PRIMARY, ArchivePurpose.COPY):
                publisher.C_doFTPArchive(careful_indexing)
            else:
                publisher.C_writeIndexes(careful_indexing)
            self.txn.commit()

        if self.options.enable_release:
            publisher.D_writeReleaseFiles(self.isCareful(
                self.options.careful_apt or self.options.careful_release))
            # The caller will commit this last step.

        if self.options.enable_apt:
            publisher.createSeriesAliases()

    def main(self):
        """See `LaunchpadScript`."""
        self.validateOptions()
        self.logOptions()

        for distribution in self.findDistros():
            allowed_suites = self.findAllowedSuites(distribution)
            for archive in self.getTargetArchives(distribution):
                publisher = self.getPublisher(
                    distribution, archive, allowed_suites)

                if archive.status == ArchiveStatus.DELETING:
                    work_done = self.deleteArchive(archive, publisher)
                elif archive.can_be_published:
                    for suite in self.options.dirty_suites:
                        distroseries, pocket = self.findSuite(
                            distribution, suite)
                        if not cannot_modify_suite(
                                archive, distroseries, pocket):
                            publisher.markPocketDirty(distroseries, pocket)
                    self.publishArchive(archive, publisher)
                    work_done = True
                else:
                    work_done = False

                if work_done:
                    self.txn.commit()

        self.logger.debug("Ciao")
