#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Copy publications across suites."""

import _pythonpath

import os

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.interfaces import (
    IDistributionSet, NotFoundError)
from canonical.launchpad.scripts.base import (LaunchpadScript,
    LaunchpadScriptFailure)
from canonical.lp import READ_COMMITTED_ISOLATION
from canonical.lp.dbschema import PackagePublishingPocket


class PackageLocationError(Exception):
    """XXX."""


class PackageLocation:
    """XXX."""
    distribution = None
    distrorelease = None
    pocket = None

    def __init__(self, distribution_name, suite_name):
        """XXX."""
        try:
            self.distribution = getUtility(IDistributionSet)[distribution_name]
        except NotFoundError, err:
            raise PackageLocationError(
                "Could not find distribution %s" % err)

        if suite_name is not None:
            suite = self.distribution.getDistroReleaseAndPocket(suite_name)
            self.distrorelease, self.pocket = suite
        else:
            self.distrorelease = self.distribution.currentrelease
            self.pocket = PackagePublishingPocket.RELEASE

    def __eq__(self, other):
        """XXX."""
        if (self.distribution.id == other.distribution.id and
            self.distrorelease.id == other.distrorelease.id and
            self.pocket.value == other.pocket.value):
            return True
        return False

    def __ne__(self, other):
        """XXX."""
        return not self.__eq__(other)

    def __str__(self):
        """XXX."""
        return '%s/%s/%s' % (self.distribution.name, self.distrorelease.name,
                             self.pocket.name)

    def __repr__(self):
        """XXX."""
        return self.__str__()


class CopyPackageHelperError(Exception):
    """XXX"""


class CopyPackageHelper:
    synced = False

    def __init__(self, logger, confirm_all, comment, sourcename,
                 sourceversion, from_distribution_name,
                 to_distribution_name, to_suite, from_suite):
        """XXX."""
        self.logger = logger
        self.confirm_all = confirm_all
        self.comment = comment
        self.sourcename = sourcename
        self.sourceversion = sourceversion
        self.from_distribution_name = from_distribution_name
        self.to_distribution_name = to_distribution_name
        self.from_suite = from_suite
        self.to_suite = to_suite

        self.target_source = None
        self.target_binaries = list()

    def _buildLocations(self):
        """XXX."""
        try:
            self.from_location = PackageLocation(
                self.from_distribution_name, self.from_suite)
            self.to_location = PackageLocation(
                self.to_distribution_name, self.to_suite)
        except PackageLocationError, err:
            raise CopyPackageHelperError(err)

        if self.from_location == self.to_location:
            raise CopyPackageHelperError(
                "Can not sync between the same locations: '%s' to '%s'" % (
                self.from_location, self.to_location))

    def _buildSource(self):
        """XXX."""
        sourcepackage = self.from_location.distrorelease.getSourcePackage(
            self.sourcename)

        if sourcepackage is None:
            raise CopyPackageHelperError(
                "Could not find any version of '%s' in %s" % (
                self.sourcename, self.from_location))

        if self.sourceversion is None:
            self.target_source = sourcepackage.currentrelease
        else:
            self.target_source = sourcepackage[self.sourceversion]

        if self.target_source is None:
            raise CopyPackageHelperError(
                "Could not find '%s/%s' in %s" % (
                self.sourcename, self.sourceversion,
                self.from_location))

    def _buildBinaries(self):
        """Build self.target_binaries with a list of distro arch release
        binary packages.  Ensure _buildSources is called before this."""
        # Obtain names of all binary packages resulting from this 
        # source version.
        # XXX does this need to be a set?
        binary_name_set = set([binary.name 
                               for binary in self.target_source.binaries])
        # Get the binary packages in each distroarchrelease and store them
        # in target_binaries for later.
        for binary_name in binary_name_set:
            for distroarchrelease in self.from_location.distrorelease.architectures:
                darbp = distroarchrelease.getBinaryPackage(binary_name)
                try:
                    # only include currently published binaries
                    current = darbp.current_published
                except NotFoundError:
                    pass
                else:
                    self.target_binaries.append(darbp)

    def _requestFeedback(self, question='Are you sure', valid_answers=None):
        """XXX."""
        answer = None
        if valid_answers:
            display_answers = '[%s]' % (', '.join(valid_answers))
            full_question = '%s ? %s ' % (question, display_answers)
            while answer not in valid_answers:
                answer = raw_input(full_question)
        else:
            full_question = '%s ? ' % question
            answer = raw_input(full_question)
        return answer

    def _displayInfo(self):
        """XXX."""
        self.logger.info(
            "Syncing '%s' TO '%s'" % (self.target_source.title,
                                      self.to_location))
        self.logger.info("Comment: %s" % self.comment)

    def performCopy(self):
        """XXX."""
        self._buildLocations()
        self._buildSource()
        self._buildBinaries()

        self._displayInfo()

        if not self.confirm_all:
            confirmation = self._requestFeedback(valid_answers=['yes', 'no'])
            if confirmation != 'yes':
                self.logger.info("Ok, see you later")
                return

        self.logger.info("Performing copy.")

        copy = self.target_source.copyTo(
            distrorelease=self.to_location.distrorelease,
            pocket=self.to_location.pocket)
        for binary in self.target_binaries:
            # copyTo will raise an error if the target distro is not released
            # in the same architecture, or the binary is not published.
            try:
                sbpph = binary.copyTo(
                    distrorelease=self.to_location.distrorelease,
                    pocket=self.to_location.pocket)
            except NotFoundError:
                pass

        self.logger.info(
            "Copied to %s/%s" % (copy.distrorelease.name, copy.pocket.title))
        self.synced = True


class CopyPackage(LaunchpadScript):
    usage = '%prog SRC DEST'
    description = 'MOVE or COPY a published package to another suite.'

    def add_my_options(self):
        """XXX. """
        self.parser.add_option(
            '-n', '--dry-run', dest='dryrun', default=False,
            action='store_true', help='Do not commit changes.')

        self.parser.add_option(
            '-y', '--confirm-all', dest='confirm_all', default=False,
            action='store_true', help='Do not prompt the user for questions.')

        self.parser.add_option(
            '-c', '--comment', dest='comment', default='',
            action='store', help='Copy comment.')

        self.parser.add_option(
            '-d', '--from-distribution', dest='from_distribution_name',
            default='ubuntu', action='store',
            help='Optional source distribution.')

        self.parser.add_option(
            '--to-distribution', dest='to_distribution_name',
            default='ubuntu', action='store',
            help='Optional destination distribution.')

        self.parser.add_option(
            '-s', '--from-suite', dest='from_suite', default=None,
            action='store', help='Optional source suite.')

        self.parser.add_option(
            '--to-suite', dest='to_suite', default=None,
            action='store', help='Optional destination suite.')

        self.parser.add_option(
            '-e', '--sourceversion', dest='sourceversion', default=None,
            action='store',
            help='Optional Source Version, defaults to the current version.')

    def main(self):
        """XXX. """
        self.txn.set_isolation_level(READ_COMMITTED_ISOLATION)

        if len(self.args) != 1:
            raise LaunchpadScriptFailure(
                "At least one non-option argument must be given, "
                "the sourcename.")

        copy_helper = CopyPackageHelper(
            logger=self.logger,
            confirm_all=self.options.confirm_all,
            comment=self.options.comment,
            sourcename=self.args[0],
            sourceversion=self.options.sourceversion,
            from_distribution_name=self.options.from_distribution_name,
            to_distribution_name=self.options.to_distribution_name,
            from_suite=self.options.from_suite,
            to_suite=self.options.to_suite)

        try:
            copy_helper.performCopy()
        except CopyPackageHelperError, err:
            raise LaunchpadScriptFailure(err)

        if copy_helper.synced and not self.options.dryrun:
            self.txn.commit()
        else:
            self.logger.info('Nothing to commit.')
            self.txn.abort()

        self.logger.info('Done.')

if __name__ == '__main__':
    script = CopyPackage('copy-package', dbuser='lucille')
    script.lock_and_run()

