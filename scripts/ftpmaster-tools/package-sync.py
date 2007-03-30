#!/usr/bin/python
# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Script to synchronise publications across suites"""

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


class PackageSyncLocationError(Exception):
    """XXX."""


class PackageSyncLocation:
    """XXX."""
    distribution = None
    distrorelease = None
    pocket = None

    def __init__(self, distribution_name, suite_name):
        """ """
        try:
            self.distribution = getUtility(IDistributionSet)[distribution_name]
        except NotFoundError, err:
            raise PackageSyncLocationError(
                "Could not find distribution %s" % err)

        if suite_name is not None:
            suite = self.distribution.getDistroReleaseAndPocket(suite_name)
            self.distrorelease, self.pocket = suite
        else:
            self.distrorelease = self.distribution.currentrelease
            self.pocket = PackagePublishingPocket.RELEASE

    def __eq__(self, other):
        """ """
        if (self.distribution.id == other.distribution.id and
            self.distrorelease.id == other.distrorelease.id and
            self.pocket.value == other.pocket.value):
            return True
        return False

    def __ne__(self, other):
        """ """
        return not self.__eq__(other)

    def __str__(self):
        """ """
        return '%s/%s/%s' % (self.distribution.name, self.distrorelease.name,
                             self.pocket.name)

    def __repr__(self):
        """ """
        return self.__str__()


class PackageSyncHelperError(Exception):
    """XXX"""


class PackageSyncHelper:
    synced = False

    def __init__(self, logger, sourcename, sourceversion,
                 from_distribution_name, to_distribution_name,
                 to_suite, from_suite):
        """ """
        self.logger = logger
        self.sourcename = sourcename
        self.sourceversion = sourceversion
        self.from_distribution_name = from_distribution_name
        self.to_distribution_name = to_distribution_name
        self.from_suite = from_suite
        self.to_suite = to_suite
        self._buildLocations()
        self._buildSource()

    def _buildLocations(self):
        """ """
        try:
            self.from_location = PackageSyncLocation(
                self.from_distribution_name, self.from_suite)
            self.to_location = PackageSyncLocation(
                self.to_distribution_name, self.to_suite)
        except PackageSyncLocationError, err:
            raise PackageSyncHelperError(err)

        if self.from_location == self.to_location:
            raise PackageSyncHelperError(
                "Can not sync between the same locations: '%s' to '%s'" % (
                self.from_location, self.to_location))

    def _buildSource(self):
        """ """
        sourcepackage = self.from_location.distrorelease.getSourcePackage(
            self.sourcename)
        if self.sourceversion is None:
            self.target_source = sourcepackage.currentrelease
        else:
            self.target_source = sourcepackage[self.sourceversion]

        if self.target_source is None:
            raise PackageSyncHelperError(
                "Could not find '%s/%s' in %s" % (
                self.sourcename, self.sourceversion,
                self.from_location))

    def _requestFeedback(self, question='Are you sure', valid_answers=None):
        """ """
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
        """ """
        self.logger.info(
            "Syncing '%s' TO '%s'" % (self.target_source.title,
                                      self.to_location))
        self.logger.info("Comment: %s" % self.comment)

    def performSync(self):
        """ """
        self.comment = self._requestFeedback(question='Sync comment')
        self._displayInfo()

        confirmation = self._requestFeedback(valid_answers=['yes', 'no'])
        if confirmation != 'yes':
            self.logger.info("Ok, see you later")
            return

        self.logger.info("Performing sync.")

        #self.to_location.distrorelease.createQueueEntry(
        #    pocket=self.to_location.pocket,
        #    changesfilename='foo_bar.changes'
        # self.synced = True


class PackageSync(LaunchpadScript):
    usage = '%prog SRC DEST'
    description = 'MOVE or COPY a published package to another suite.'

    def add_my_options(self):
        """XXX. """
        self.parser.add_option(
            '-n', '--dry-run', dest='dryrun', default=False,
            action='store_true', help='Do not commit changes.')

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

        try:
            sync_helper = PackageSyncHelper(
                logger=self.logger,
                sourcename=self.args[0],
                sourceversion=self.options.sourceversion,
                from_distribution_name=self.options.from_distribution_name,
                to_distribution_name=self.options.to_distribution_name,
                from_suite=self.options.from_suite,
                to_suite=self.options.to_suite)
            sync_helper.performSync()
        except PackageSyncHelperError, err:
            raise LaunchpadScriptFailure(err)

        if sync_helper.synced and not self.options.dryrun:
            self.txn.commit()
        else:
            self.logger.info('Nothing to commit.')
            self.txn.abort()

        self.logger.info('Done.')

if __name__ == '__main__':
    script = PackageSync('package-sync', dbuser=config.uploader.dbuser)
    script.lock_and_run()

