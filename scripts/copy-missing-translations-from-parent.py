#!/usr/bin/python2.4
# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Furnish distrorelease with lacking translations that its parent does have.

This can be used either to update a distrorelease's translations, or to
provide a new distrorelease in a series with its initial translation data.
Only current translations are copied.
"""

import _pythonpath
from zope.component import getUtility
from canonical.config import config
from canonical.launchpad.interfaces import IDistributionSet
from canonical.launchpad.scripts.base import LaunchpadScript

class TranslationsCopier(LaunchpadScript):
    """A LaunchpadScript for copying distrorelease translations from parent.

    Core job is to invoke distrorelease.copyMissingTranslationsFromParent().
    """

    def add_my_options(self):
        self.parser.add_option('-d', '--distribution', dest='distro',
            default='ubuntu',
            help='Name of distribution to copy translations in.')
        self.parser.add_option('-r', '--release', dest='release',
            help='Name of distrorelease whose translations should be updated')

    def main(self):
        distribution = getUtility(IDistributionSet)[self.options.distro]
        release = distribution[self.options.release]

        self.logger.info('Starting...')
        release.copyMissingTranslationsFromParent(self.txn)

        # We would like to update the DistroRelase statistics, but it takes
        # too long so this should be done after.
        #
        # Finally, we changed many things related with cached statistics, so
        # we may want to update those.
        # self.logger.info('Updating DistroRelease statistics...')
        # release.updateStatistics(self.txn)
        self.logger.info('Done...')

        # Commit our transaction.
        self.txn.commit()

    @property
    def lockfilename(self):
        """Return lock file name for this script on this distrorelease.

        No global lock is needed, only one for the distrorelease we operate
        on.  This does mean that our options must have been parsed before this
        property is ever accessed.  Luckily that is what LaunchpadScript does!
        """
        return "launchpad-%s-%s-%s.lock" % (self.name, self.options.distro,
            self.options.release)


if __name__ == '__main__':

    script = TranslationsCopier('copy-missing-translations',
        dbuser=config.rosetta.poimport.dbuser)

    script.lock_and_run()

