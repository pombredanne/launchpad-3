#!/usr/bin/python2.4
# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Furnish distroseries with lacking translations that its parent does have.

This can be used either to update a distroseries' translations, or to
provide a new distroseries in a series with its initial translation data.
Only current translations are copied.
"""

import _pythonpath
import sys
from zope.component import getUtility
from canonical.config import config
from canonical.launchpad.interfaces import IDistributionSet
from canonical.launchpad.scripts.base import LaunchpadScript


class TranslationsCopier(LaunchpadScript):
    """A LaunchpadScript for copying distroseries translations from parent.

    Core job is to invoke distroseries.copyMissingTranslationsFromParent().
    """

    def add_my_options(self):
        self.parser.add_option('-d', '--distribution', dest='distro',
            default='ubuntu',
            help='Name of distribution to copy translations in.')
        self.parser.add_option('-s', '--series', dest='series',
            help='Name of distroseries whose translations should be updated')

    def main(self):
        distribution = getUtility(IDistributionSet)[self.options.distro]
        series = distribution[self.options.series]

        if (not series.hide_all_translations or
            not series.defer_translation_imports):
            # We cannot start the process, precondition is not meet.
            self.txn.abort()
            self.logger.error(
                'Before this process starts, you should set'
                ' hide_all_translations and defer_translation_imports flags'
                ' for the distribution %s, series %s' % (
                    self.options.distro, self.options.series))
            sys.exit(1)

        self.logger.info('Starting...')
        series.copyMissingTranslationsFromParent(self.txn, self.logger)

        # We would like to update the DistroRelase statistics, but it takes
        # too long so this should be done after.
        #
        # Finally, we changed many things related with cached statistics, so
        # we may want to update those.
        # self.logger.info('Updating DistroRelease statistics...')
        # series.updateStatistics(self.txn)
        self.logger.info('Done...')

        # Commit our transaction.
        self.txn.commit()

    @property
    def lockfilename(self):
        """Return lock file name for this script on this distroseries.

        No global lock is needed, only one for the distroseries we operate
        on.  This does mean that our options must have been parsed before this
        property is ever accessed.  Luckily that is what LaunchpadScript does!
        """
        return "launchpad-%s-%s-%s.lock" % (self.name, self.options.distro,
            self.options.series)


if __name__ == '__main__':

    script = TranslationsCopier(
        'copy-missing-translations', dbuser=config.rosetta.poimport.dbuser)

    script.lock_and_run()

