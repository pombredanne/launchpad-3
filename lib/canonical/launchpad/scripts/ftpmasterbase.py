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
    ]

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IDistributionSet, NotFoundError, IComponentSet)
from canonical.launchpad.scripts.base import (
    LaunchpadScript, LaunchpadScriptFailure)
from canonical.lp.dbschema import PackagePublishingPocket


class PackageLocationError(Exception):
    """Raised when something went wrong when building PackageLocation."""


class PackageLocation:
    """Object used to model locations when copying publications.


    It groups distribution, distroseries and pocket in a way they
    can be easily manipulated and compared.
    """
    distribution = None
    distroseries = None
    pocket = None

    def __init__(self, distribution_name, suite_name):
        """Initialize the PackageLocation from the given parameters.

        Build Launchpad objects and expand suite_name into distroseries and
        pocket.
        """
        try:
            self.distribution = getUtility(IDistributionSet)[distribution_name]
        except NotFoundError, err:
            raise PackageLocationError(
                "Could not find distribution %s" % err)

        if suite_name is not None:
            try:
                suite = self.distribution.getDistroSeriesAndPocket(suite_name)
            except NotFoundError, err:
                raise PackageLocationError(
                    "Could not find suite %s" % err)
            else:
                self.distroseries, self.pocket = suite
        else:
            self.distroseries = self.distribution.currentseries
            self.pocket = PackagePublishingPocket.RELEASE

    def __eq__(self, other):
        if (self.distribution == other.distribution and
            self.distroseries == other.distroseries and
            self.pocket == other.pocket):
            return True
        return False

    def __str__(self):
        return '%s/%s/%s' % (self.distribution.name, self.distroseries.name,
                             self.pocket.name)


class SoyuzScriptError(Exception):
    """Raised when a soyuz script failed.

    The textual content should explain the error.
    """


class SoyuzScript(LaunchpadScript):
    """`LaunchpadScript` extended for Soyuz related use.

    Possible exceptions raised are:

     * `PackageLocationError`: specified package or distro does not exist
     * `PackageRemoverError`: the remove operation itself has failed
     * `LaunchpadScriptError`: only raised if entering via main(), ie this
        code is running as a genuine script.  In this case, this is
        also the _only_ exception to be raised.

    The test harness doesn't enter via main(), it calls task(), so
    it only sees the first two exceptions.

    Each script can extend:

     * `usage`: string describing the expected command-line format;
     * `description`: string describing the tool;
     * `success_message`: string to be presented on successful runs;
     * `addExtraSoyuzOption`: a method to include extra command-line options;
     * `mainTask`: a method to actually perform a specific task.

    See self.add_my_options contexts for the default `SoyuzScript`
    command-line options.
    """
    success_message = "Done."

    def add_my_options(self):
        """Adds SoyuzScript default options.

        Also adds the callsite options defined via self.addExtraSoyuzOptions.
        """
        self.parser.add_option(
            '-n', '--dry-run', dest='dryrun', default=False,
            action='store_true', help='Do not commit changes.')

        self.parser.add_option(
            '-y', '--confirm-all', dest='confirm_all',
            default=False, action='store_true',
            help='Do not prompt the user for confirmation.')

        self.parser.add_option(
            '-d', '--distribution', dest='distribution_name',
            default='ubuntu', action='store',
            help='Distribution name.')

        self.parser.add_option(
            '-s', '--suite', dest='suite', default=None,
            action='store', help='Suite name.')

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

        self.addExtraSoyuzOptions()

    def addExtraSoyuzOptions(self):
        """Hook to allow command-line customization.

        Similar to `LaunchpadScript.add_my_options`.
        """
        pass

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

    def findSource(self, name):
        """Return a suitable `DistroSeriesSourcePackageRelease`."""
        assert self.location is not None, 'Undefined location.'

        sourcepackage = self.location.distroseries.getSourcePackage(name)
        if sourcepackage is None:
            raise SoyuzScriptError(
                "Could not find any source version of '%s' in %s" % (
                name, self.location))
        if self.options.version is None:
            target_source = sourcepackage.currentrelease
        else:
            target_source = sourcepackage[self.options.version]

        if target_source is None:
            raise SoyuzScriptError(
                "Could not find source '%s/%s' in %s" % (
                name, self.options.version, self.location))

        self._validatePublishing(target_source.current_published)

        return target_source

    def findBinaries(self, name):
        """Build a list of suitable `DistroArchSeriesBinaryPackageRelease`.

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
            binarypackage = architecture.getBinaryPackage(name)
            if binarypackage is None:
                continue

            if self.options.version is None:
                target_binary = binarypackage.currentrelease
            else:
                target_binary = binarypackage[self.options.version]
            if target_binary is None:
                continue
            try:
                self._validatePublishing(
                    target_binary.current_publishing_record)
            except SoyuzScriptError, err:
                self.logger.warn(err)
            else:
                target_binaries.append(target_binary)

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

        Return True immediatelly if options.confirm_all was passed or after
        getting a valid confirmation, False otherwise.
        """
        if not self.options.confirm_all and not self._getUserConfirmation():
            return False
        return True

    def setupLocation(self):
        """Setup `PackageLocation` for context distribution and suite."""
        # These can raise PackageLocationError, but we're happy to pass
        # it upwards.
        try:
            self.location = PackageLocation(
                self.options.distribution_name, self.options.suite)
        except PackageLocationError, err:
            raise SoyuzScriptError(err)

    def _finishProcedure(self):
        """Script finalization procedure.

        'dry-run' command-line option will case the transaction to be
        immediatelly aborted.

        In normal mode it will ask for user confirmation (see
        `waitForUserConfirmation`) and will commit the transaction or abort
        it according to the user answer.
        """
        if self.options.dryrun:
            self.logger.info('Dry run, so nothing to commit.')
            self.txn.abort()
            return

        confirmed = self.waitForUserConfirmation()

        if confirmed:
            self.txn.commit()
            self.logger.info('Transaction committed.')
            self.logger.info(self.success_message)
        else:
            self.logger.info("Ok, see you later")
            self.txn.abort()

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

        self._finishProcedure()

    def mainTask(self):
        """Main task to be performed by the script"""
        raise NotImplementedError
