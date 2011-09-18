#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).


"""Tool for 'mass-retrying' build records.

It supports build collections based distroseries and/or distroarchseries.
"""

__metaclass__ = type

import _pythonpath

import transaction
from zope.component import getUtility

from lp.app.errors import NotFoundError
from lp.buildmaster.enums import BuildStatus
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.scripts.base import LaunchpadScript


class BuilddMassRetryScript(LaunchpadScript):

    dbuser = "fiera"

    def add_my_options(self):
        self.parser.add_option(
            "-d", "--distribution", dest="distribution",
            metavar="DISTRIBUTION", default="ubuntu",
            help="distribution name")

        self.parser.add_option(
            "-s", "--suite", dest="suite", metavar="SUITE", help="suite name")

        self.parser.add_option(
            "-a", "--architecture", dest="architecture", metavar="ARCH",
            help="architecture tag")

        self.parser.add_option(
            "-N", "--dry-run", action="store_true", dest="dryrun",
            metavar="DRY_RUN", default=False,
            help="Whether to treat this as a dry-run or not.")

        self.parser.add_option(
            "-F", "--failed", action="store_true", dest="failed",
            default=False, help="Reset builds in FAILED state.")

        self.parser.add_option(
            "-D", "--dep-wait", action="store_true", dest="depwait",
            default=False, help="Reset builds in DEPWAIT state.")

        self.parser.add_option(
            "-C", "--chroot-wait", action="store_true", dest="chrootwait",
            default=False, help="Reset builds in CHROOTWAIT state.")

    def main(self):
        options = self.options
        log = self.logger

        try:
            distribution = getUtility(IDistributionSet)[options.distribution]
        except NotFoundError, info:
            log.error("Distribution not found: %s" % info)
            return 1

        try:
            if options.suite is not None:
                series, pocket = distribution.getDistroSeriesAndPocket(
                    options.suite)
            else:
                series = distribution.currentseries
                pocket = PackagePublishingPocket.RELEASE
        except NotFoundError, info:
            log.error("Suite not found: %s" % info)
            return 1

        # store distroseries as the current IHasBuildRecord provider
        build_provider = series

        if options.architecture:
            try:
                dar = series[options.architecture]
            except NotFoundError, info:
                log.error(info)
                return 1

            # store distroarchseries as the current IHasBuildRecord provider
            build_provider = dar

        log.info("Initializing Build Mass-Retry for '%s/%s'"
                % (build_provider.title, pocket.name))

        requested_states_map = {
            BuildStatus.FAILEDTOBUILD : options.failed,
            BuildStatus.MANUALDEPWAIT : options.depwait,
            BuildStatus.CHROOTWAIT : options.chrootwait,
            }

        # XXX cprov 2006-08-31: one query per requested state
        # could organise it in a single one nicely if I have
        # an empty SQLResult instance, than only iteration + union()
        # would work.
        for target_state, requested in requested_states_map.items():
            if not requested:
                continue

            log.info("Processing builds in '%s'" % target_state.title)
            target_builds = build_provider.getBuildRecords(
                build_state=target_state, pocket=pocket)

            for build in target_builds:
                # Skip builds for superseded sources; they won't ever
                # actually build.
                if not build.current_source_publication:
                    log.debug(
                        'Skipping superseded %s (%s)' % (build.title, build.id))
                    continue

                if not build.can_be_retried:
                    log.warn('Can not retry %s (%s)' % (build.title, build.id))
                    continue

                log.info('Retrying %s (%s)' % (build.title, build.id))
                build.retry()

        log.info("Success.")

        if options.dryrun:
            transaction.abort()
            log.info('Dry-run.')
        else:
            transaction.commit()
            log.info("Committed")

        return 0


if __name__ == '__main__':
    BuilddMassRetryScript('buildd-mass-retry', 'fiera').lock_and_run()
