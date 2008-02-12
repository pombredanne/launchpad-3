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
from canonical.launchpad.scripts.base import LaunchpadCronScript


class TranslationsCopier(LaunchpadCronScript):
    """Copy latest distroseries translations from parent series.

    Core job is to invoke `distroseries.copyMissingTranslationsFromParent()`.
    """

    def add_my_options(self):
        self.parser.add_option('-d', '--distribution', dest='distro',
            default='ubuntu',
            help='Name of distribution to copy translations in.')
        self.parser.add_option('-s', '--series', dest='series',
            help='Name of distroseries whose translations should be updated')
        self.parser.add_option('-f', '--force', dest='force',
            action="store_true", default=False,
            help="Don't check if target's UI and imports are blocked; "
                 "actively block them.")

    def _getTargetSeries(self):
        """Retrieve target `DistroSeries`."""
        distro = self.options.distro
        series = self.options.series
        return getUtility(IDistributionSet)[distro][series]

    def main(self):
        distribution = getUtility(IDistributionSet)[self.options.distro]
        series = self._getTargetSeries()

        series_hide_translations = series.hide_all_translations
        series_defer_imports = series.defer_translation_imports
        blocked = (series_hide_translations and series_defer_imports)

        if not blocked:
            if not self.options.force:
                self.txn.abort()
                self.logger.error(
                    'Before this process starts, set the '
                    'hide_all_translations and defer_translation_imports '
                    'flags for distribution %s, series %s; or use the '
                    '--force option to make it happen automatically.' % (
                        self.options.distro, self.options.series))
                sys.exit(1)

            series.hide_all_translations = True
            series.defer_translation_imports = True
            self.txn.commit()
            self.txn.begin()

        self.logger.info('Starting...')

        try:
            # Do the actual work.
            series.copyMissingTranslationsFromParent(self.txn, self.logger)
        finally:
            # We've crossed transaction boundaries.  Remember to forget the
            # old ORM object.
            series = None

            if not blocked:
                # We messed with the series' flags.  Restore them.
                series = self._getTargetSeries()
                changed = (
                    series.hide_all_translations !=
                        series_hide_translations or
                    series.defer_translation_imports != series_defer_imports)
                if changed:
                    # The flags have been changed while we were working.  Play
                    # safe and don't touch them.
                    self.logger.warning("Translations flags for %s have been "
                        "changed while copy was in progress: "
                        "hide_all_translations was %d, is now %d; "
                        "defer_translation_imports was %d and is now %d. "
                        "Please review this change, since it may affect "
                        "users' ability to work on this series' translations."
                            % (self.options.series,
                               series_hide_translations,
                               series.hide_all_translations,
                               series_defer_imports,
                               series.defer_translation_imports))
                else:
                    # No worries.  Restore flags.
                    series.hide_all_translations = series_hide_translations
                    series.defer_translation_imports = series_defer_imports

        # We would like to update the DistroRelase statistics, but it takes
        # too long so this should be done after.
        #
        # Finally, we changed many things related with cached statistics, so
        # we may want to update those.
        # self.logger.info('Updating DistroSeries statistics...')
        # series.updateStatistics(self.txn)

        self.txn.commit()

        self.logger.info('Done...')

    @property
    def lockfilename(self):
        """Return lock file name for this script on this distroseries.

        No global lock is needed, only one for the distroseries we operate
        on.  This does mean that our options must have been parsed before this
        property is ever accessed.  Luckily that is what the `LaunchpadScript`
        code does!
        """
        return "launchpad-%s-%s-%s.lock" % (self.name, self.options.distro,
            self.options.series)


if __name__ == '__main__':

    script = TranslationsCopier(
        'copy-missing-translations', dbuser=config.rosetta.poimport.dbuser)

    script.lock_and_run()

