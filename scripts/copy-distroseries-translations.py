#!/usr/bin/python -S
#
# Copyright 2009-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Furnish distroseries with lacking translations that its parent does have.

This can be used either to update a distroseries' translations, or to
provide a new distroseries in a series with its initial translation data.
Only current translations are copied.
"""

import _pythonpath

import sys

from zope.component import getUtility

from lp.registry.interfaces.distribution import IDistributionSet
from lp.services.scripts.base import LaunchpadCronScript
from lp.soyuz.interfaces.archive import IArchiveSet
from lp.translations.scripts.copy_distroseries_translations import (
    copy_distroseries_translations,
    )


class TranslationsCopier(LaunchpadCronScript):
    """Copy latest distroseries translations from parent series.

    Core job is to invoke `distroseries.copyMissingTranslationsFromParent()`.
    """

    def add_my_options(self):
        self.parser.add_option('-d', '--distribution', dest='distro',
            default='ubuntu',
            help='The target distribution.')
        self.parser.add_option('-s', '--series', dest='series',
            help='The target distroseries.')
        self.parser.add_option('--from-distribution', dest='from_distro',
            help=(
                "The source distribution (if omitted, target's previous "
                "series will be used)."))
        self.parser.add_option('--from-series', dest='from_series',
            help=(
                "The source distroseries (if omitted, target's previous "
                "series will be used)."))
        self.parser.add_option(
            '--published-sources-only', dest='published_sources_only',
            action="store_true", default=False,
            help=(
                "Copy only templates for sources that are published in the "
                "target series."))
        self.parser.add_option('--check-archive', dest='check_archive',
            help=(
                "With --published-sources-only, check publication in this "
                "archive (if omitted, the target's main archive will be "
                "checked)."))
        self.parser.add_option('--check-distroseries',
            dest='check_distroseries',
            help=(
                "With --published-sources-only, check publication in this "
                "distroseries (if omitted, the target distroseries will be "
                "checked)."))
        self.parser.add_option('-f', '--force', dest='force',
            action="store_true", default=False,
            help="Don't check if target's UI and imports are blocked; "
                 "actively block them.")

    def main(self):
        target = getUtility(IDistributionSet)[self.options.distro][
            self.options.series]
        if self.options.from_distro:
            source = getUtility(IDistributionSet)[self.options.from_distro][
                self.options.from_series]
        else:
            source = target.previous_series
        if source is None:
            self.parser.error(
                "No source series specified and target has no previous "
                "series.")
        if self.options.check_archive is not None:
            check_archive = getUtility(IArchiveSet).getByReference(
                self.options.check_archive)
        else:
            check_archive = target.main_archive
        check_distribution = check_archive.distribution
        if self.options.check_distroseries is not None:
            check_distroseries = check_distribution[
                self.options.check_distroseries]
        else:
            check_distroseries = check_distribution[self.options.series]

        # Both translation UI and imports for this series should be blocked
        # while the copy is in progress, to reduce the chances of deadlocks or
        # other conflicts.
        blocked = (
            target.hide_all_translations and target.defer_translation_imports)
        if not blocked and not self.options.force:
            self.txn.abort()
            self.logger.error(
                'Before this process starts, set the '
                'hide_all_translations and defer_translation_imports '
                'flags for distribution %s, series %s; or use the '
                '--force option to make it happen automatically.' % (
                    self.options.distro, self.options.series))
            sys.exit(1)

        self.logger.info('Starting...')

        # Actual work is done here.
        copy_distroseries_translations(
            source, target, self.txn, self.logger,
            published_sources_only=self.options.published_sources_only,
            check_archive=check_archive, check_distroseries=check_distroseries)

        # We would like to update the DistroRelase statistics, but it takes
        # too long so this should be done after.
        #
        # Finally, we changed many things related with cached statistics, so
        # we may want to update those.
        # self.logger.info('Updating DistroSeries statistics...')
        # series.updateStatistics(self.txn)

        self.txn.commit()
        self.logger.info('Done.')

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
        'copy-missing-translations', dbuser='translations_distroseries_copy')
    script.lock_and_run()
