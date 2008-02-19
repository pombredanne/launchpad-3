# Copyright 2007 Canonical Ltd.  All rights reserved.
"""Buildd cronscript classes """

__metaclass__ = type

__all__ = [
    'RetryDepwait',
    ]

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    DistroSeriesStatus, IBuildSet, IDistributionSet, NotFoundError)
from canonical.launchpad.scripts.base import (
    LaunchpadCronScript, LaunchpadScriptFailure)


class RetryDepwait(LaunchpadCronScript):

    def add_my_options(self):
        self.parser.add_option(
            "-d", "--distribution", default="ubuntu",
            help="Context distribution.")

        self.parser.add_option(
            "-n", "--dry-run",
            dest="dryrun", action="store_true", default=False,
            help="Whether or not to commit the transaction.")

    def main(self):
        """Retry all builds that do not fit in MANUALDEPWAIT.

        Iterate over all supported series in the given distribution and
        their architectures with existent chroots and update all builds
        found in MANUALDEPWAIT status.
        """
        if self.args:
            raise LaunchpadScriptFailure("Unhandled arguments %r" % self.args)

        distribution_set = getUtility(IDistributionSet)
        try:
            distribution = distribution_set[self.options.distribution]
        except NotFoundError:
            raise LaunchpadScriptFailure(
                "Could not find distribution: %s" % self.options.distribution)

        # Iterate over all supported distroarchseries with available chroot.
        build_set = getUtility(IBuildSet)
        for distroseries in distribution:
            if distroseries.status == DistroSeriesStatus.OBSOLETE:
                self.logger.debug(
                    "Skipping obsolete distroseries: %s" % distroseries.title)
                continue
            for distroarchseries in distroseries.architectures:
                self.logger.info("Processing %s" % distroarchseries.title)
                if not distroarchseries.getChroot:
                    self.logger.debug("Chroot not found")
                    continue
                build_set.retryDepWaiting(distroarchseries)

        # XXX cprov 20071122:  LaunchpadScript should provide some
        # infrastructure for dry-run operations and not simply rely
        # on the transaction being discarded by the garbage-collector.
        # See further information in bug #165200.
        if not self.options.dryrun:
            self.logger.info('Commiting the transaction.')
            self.txn.commit()
