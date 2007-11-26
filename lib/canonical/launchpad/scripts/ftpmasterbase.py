# Copyright 2007 Canonical Ltd.  All rights reserved.
"""FTPMaster base classes.

PackageLocation and SoyuzScript.
"""

__metaclass__ = type

__all__ = [
    'PackageLocationError',
    'PackageLocation',
    'SoyuzScriptError',
    'SoyuzScript',
    'build_package_location',
    ]

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    ArchivePurpose, IArchiveSet, IComponentSet, IDistributionSet,
    NotFoundError, PackagePublishingPocket, PackagePublishingStatus)
from canonical.launchpad.scripts.base import (
    LaunchpadScript, LaunchpadScriptFailure)


class SoyuzScriptError(Exception):
    """Raised when a soyuz script failed.

    The textual content should explain the error.
    """


class PackageLocationError(SoyuzScriptError):
    """Raised when something went wrong when building PackageLocation."""


def build_package_location(distribution_name, suite=None, purpose=None,
                           person_name=None):
    """Convenience function to build PackageLocation objects."""

    # XXX: we need a way to specify exactly what location we want
    # through strings in the commandline. Until we do, we will end up
    # with this horrible set of self-excluding options that make sense
    # to nobody. Perhaps:
    #   - ppa.launchpad.net/cprov/ubuntu/warty
    #   - archive.ubuntu.com/ubuntu-security/hoary
    #   - security.ubuntu.com/ubuntu/hoary
    #   - archive.canonical.com/gutsy
    #                                           -- kiko, 2007-10-24

    try:
        distribution = getUtility(IDistributionSet)[distribution_name]
    except NotFoundError, err:
        raise PackageLocationError(
            "Could not find distribution %s" % err)

    if purpose == ArchivePurpose.PPA:
        assert person_name is not None, (
            "person_name should be passed for PPA archives.")
        archive = getUtility(IArchiveSet).getPPAByDistributionAndOwnerName(
            distribution, person_name)
        if archive is None:
            raise PackageLocationError(
                "Could not find a PPA for %s" % person_name)
        if distribution != archive.distribution:
            raise PackageLocationError(
                "The specified archive is not for distribution %s"
                % distribution_name)
    elif purpose == ArchivePurpose.PARTNER:
        assert person_name is None, (
            "person_name shoudn't be passed for PARTNER archive.")
        archive = getUtility(IArchiveSet).getByDistroPurpose(
            distribution, purpose)
        if archive is None:
            raise PackageLocationError(
                "Could not find %s archive for %s" % (
                purpose.title, distribution_name))
    else:
        assert person_name is None, (
            "person_name shoudn't be passed when purpose is omitted.")
        archive = distribution.main_archive

    if suite is not None:
        try:
            distroseries, pocket = distribution.getDistroSeriesAndPocket(
                suite)
        except NotFoundError, err:
            raise PackageLocationError(
                "Could not find suite %s" % err)
    else:
        distroseries = distribution.currentseries
        pocket = PackagePublishingPocket.RELEASE

    return PackageLocation(archive, distribution, distroseries, pocket)


class PackageLocation:
    """Object used to model locations when copying publications.

    It groups distribution, distroseries and pocket in a way they
    can be easily manipulated and compared.
    """
    archive = None
    distribution = None
    distroseries = None
    pocket = None

    def __init__(self, archive, distribution, distroseries, pocket):
        """Initialize the PackageLocation from the given parameters."""
        self.archive = archive
        self.distribution = distribution
        self.distroseries = distroseries
        self.pocket = pocket

    def __eq__(self, other):
        if (self.distribution == other.distribution and
            self.archive == other.archive and
            self.distroseries == other.distroseries and
            self.pocket == other.pocket):
            return True
        return False

    def __str__(self):
        return '%s: %s-%s' % (self.archive.title,
                             self.distroseries.name, self.pocket.name)


class SoyuzScript(LaunchpadScript):
    """`LaunchpadScript` extended for Soyuz related use.

    Possible exceptions raised are:

     * `PackageLocationError`: specified package or distro does not exist
     * `LaunchpadScriptError`: only raised if entering via main(), ie this
        code is running as a genuine script.  In this case, this is
        also the _only_ exception to be raised.

    The test harness doesn't enter via main(), it calls task(), so
    it does not see LaunchpadScriptError.

    Each script can extend:

     * `usage`: string describing the expected command-line format;
     * `description`: string describing the tool;
     * `success_message`: string to be presented on successful runs;
     * `mainTask`: a method to actually perform a specific task.

    See `add_my_options` for the default `SoyuzScript` command-line options.
    """
    location = None
    success_message = "Done."

    def add_my_options(self):
        """Adds SoyuzScript default options."""
        self.add_transaction_options()
        self.add_distro_options()
        self.add_package_location_options()
        self.add_archive_options()

    def add_transaction_options(self):
        """Add SoyuzScript transaction-related options."""
        self.parser.add_option(
            '-n', '--dry-run', dest='dryrun', default=False,
            action='store_true', help='Do not commit changes.')

        self.parser.add_option(
            '-y', '--confirm-all', dest='confirm_all',
            default=False, action='store_true',
            help='Do not prompt the user for confirmation.')

    def add_distro_options(self):
        """Add SoyuzScript distro-related options."""
        self.parser.add_option(
            '-d', '--distribution', dest='distribution_name',
            default='ubuntu', action='store',
            help='Distribution name.')

        self.parser.add_option(
            '-s', '--suite', dest='suite', default=None,
            action='store', help='Suite name.')

    def add_package_location_options(self):
        """Add SoyuzScript package location-related options."""
        self.parser.add_option(
            "-a", "--architecture", dest="architecture", default=None,
            help="Architecture tag.")

        self.parser.add_option(
            '-e', '--version', dest='version', default=None,
            action='store',
            help='Optional package version, defaults to the current version.')

        self.parser.add_option(
            "-c", "--component", dest="component", default=None,
            help="Component name.")

    def add_archive_options(self):
        """Add SoyuzScript archive-related options."""
        self.parser.add_option(
            '-p', '--ppa', dest='archive_owner_name', action='store',
            help='Archive owner name in case of PPA operations')

        self.parser.add_option(
            '-j', '--partner', dest='partner_archive', default=False,
            action='store_true',
            help='Specify partner archive')

    def _validatePublishing(self, currently_published):
        """Validate the given publishing record.

        Check if it matches the desired 'pocket' and 'component'.
        """
        if currently_published.pocket != self.location.pocket:
            raise SoyuzScriptError(
                "%s was skipped because it is not in %s pocket." % (
                currently_published.displayname, self.location.pocket.name))

        if not self.options.component:
            return

        try:
            desired_component = getUtility(IComponentSet)[
                self.options.component]
        except NotFoundError, err:
            raise SoyuzScriptError(err)

        if currently_published.component != desired_component:
            raise SoyuzScriptError(
                "%s was skipped because it is not in %s component" % (
                currently_published.displayname,
                desired_component.name.upper()))

    def findLatestPublishedSource(self, name):
        """Return a suitable `SourcePackagePublishingHistory`."""
        assert self.location is not None, 'Undefined location.'

        published_sources = self.location.archive.getPublishedSources(
            name=name, version=self.options.version,
            status=PackagePublishingStatus.PUBLISHED,
            distroseries=self.location.distroseries,
            exact_match=True)

        if not published_sources:
            raise SoyuzScriptError(
                "Could not find source '%s/%s' in %s" % (
                name, self.options.version, self.location))

        latest_source = published_sources[0]
        self._validatePublishing(latest_source)
        return latest_source

    def findLatestPublishedBinaries(self, name):
        """Build a list of suitable `BinaryPackagePublishingHistory`.

        Try to find a group of binary package release matching the current
        context. 'architecture' or 'version', if passed via command-line,
        will restrict the lookup accordingly.
        """
        assert self.location is not None, 'Undefined location.'
        target_binaries = []

        if self.options.architecture is None:
            architectures = self.location.distroseries.architectures
        else:
            try:
                architectures = [
                    self.location.distroseries[self.options.architecture]]
            except NotFoundError, err:
                raise SoyuzScriptError(err)

        for architecture in architectures:
            binaries = self.location.archive.getAllPublishedBinaries(
                    name=name, version=self.options.version,
                    status=PackagePublishingStatus.PUBLISHED,
                    distroarchseries=architecture,
                    exact_match=True)
            if not binaries:
                continue
            binary = binaries[0]
            try:
                self._validatePublishing(binary)
            except SoyuzScriptError, err:
                self.logger.warn(err)
            else:
                target_binaries.append(binary)

        if not target_binaries:
            raise SoyuzScriptError(
                "Could not find binaries for '%s/%s' in %s" % (
                name, self.options.version, self.location))

        return target_binaries

    def _getUserConfirmation(self, full_question=None, valid_answers=None):
        """Use raw_input to collect user feedback.

        Return True if the user typed the first value of the given
        'valid_answers' (defaults to 'yes') or False otherwise.
        """
        if valid_answers is None:
            valid_answers = ['yes', 'no']
        display_answers = '[%s]' % (', '.join(valid_answers))

        if full_question is None:
            full_question = 'Confirm this transaction? %s ' % display_answers
        else:
            full_question = '%s %s' % (full_question, display_answers)

        answer = None
        while answer not in valid_answers:
            answer = raw_input(full_question)

        return answer == valid_answers[0]

    def waitForUserConfirmation(self):
        """Blocks the script flow waiting for a user confirmation.

        Return True immediately if options.confirm_all was passed or after
        getting a valid confirmation, False otherwise.
        """
        if not self.options.confirm_all and not self._getUserConfirmation():
            return False
        return True

    def setupLocation(self):
        """Setup `PackageLocation` for context distribution and suite."""
        # These can raise PackageLocationError, but we're happy to pass
        # it upwards.
        if(hasattr(self.options, 'partner_archive') and
            self.options.partner_archive is not None):
            self.location = build_package_location(
                self.options.distribution_name,
                self.options.suite,
                ArchivePurpose.PARTNER)
        elif(hasattr(self.options, 'archive_owner_name') and
             self.options.archive_owner_name is not None):
            self.location = build_package_location(
                self.options.distribution_name,
                self.options.suite,
                ArchivePurpose.PPA,
                self.options.archive_owner_name)
        else:
            self.location = build_package_location(
                self.options.distribution_name,
                self.options.suite)

    def finishProcedure(self):
        """Script finalization procedure.

        'dry-run' command-line option will case the transaction to be
        immediatelly aborted.

        In normal mode it will ask for user confirmation (see
        `waitForUserConfirmation`) and will commit the transaction or abort
        it according to the user answer.

        Returns True if the transaction was committed, False otherwise.
        """
        if self.options.dryrun:
            self.logger.info('Dry run, so nothing to commit.')
            self.txn.abort()
            return False

        confirmed = self.waitForUserConfirmation()

        if confirmed:
            self.txn.commit()
            self.logger.info('Transaction committed.')
            self.logger.info(self.success_message)
            return True
        else:
            self.logger.info("Ok, see you later")
            self.txn.abort()
            return False

    def main(self):
        """LaunchpadScript entry point.

        Can only raise LaunchpadScriptFailure - other exceptions are
        absorbed into that.
        """
        try:
            self.setupLocation()
            self.mainTask()
        except SoyuzScriptError, err:
            raise LaunchpadScriptFailure(err)

        self.finishProcedure()

    def mainTask(self):
        """Main task to be performed by the script"""
        raise NotImplementedError



