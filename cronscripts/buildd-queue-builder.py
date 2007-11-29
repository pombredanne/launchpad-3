#!/usr/bin/python2.4
# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0403
# Author: Daniel Silverstone <daniel.silverstone@canonical.com>
#         Celso Providelo <celso.providelo@canonical.com>
#
# Build Jobs initialisation
#
__metaclass__ = type

import _pythonpath

from zope.component import getUtility

from canonical.archivepublisher.debversion import Version
from canonical.config import config
from canonical.buildmaster.master import BuilddMaster

from canonical.launchpad.interfaces import IDistroArchSeriesSet
from canonical.launchpad.scripts.base import (LaunchpadCronScript,
    LaunchpadScriptFailure)


class QueueBuilder(LaunchpadCronScript):

    def add_my_options(self):
        self.parser.add_option(
            "-n", "--dry-run", action="store_true",
            dest="dryrun", metavar="DRY_RUN", default=False,
            help="Whether to treat this as a dry-run or not.")

    def main(self):
        """Invoke rebuildQueue.

        Check if the cron.daily is running, quietly exits if true.
        Force isolation level to READ_COMMITTED_ISOLATION.
        Deals with the current transaction according the dry-run option.
        """
        if self.args:
            raise LaunchpadScriptFailure("Unhandled arguments %r" % self.args)

        # In order to avoid the partial commits inside BuilddMaster
        # to happen we pass a FakeZtm instance if dry-run mode is selected.
        class _FakeZTM:
            """A fake transaction manager."""
            def commit(self):
                pass

        if self.options.dryrun:
            self.logger.info("Dry run: changes will not be committed.")
            self.txn = _FakeZTM()

        self.rebuildQueue()
        self.txn.commit()

    def rebuildQueue(self):
        """Look for and initialise new build jobs."""

        self.logger.info("Rebuilding Build Queue.")
        buildMaster = BuilddMaster(self.logger, self.txn)

        # For every distroarchseries we can find; put it into the build master
        distroserieses = set()
        for archseries in getUtility(IDistroArchSeriesSet):
            distroserieses.add(archseries.distroseries)
            buildMaster.addDistroArchSeries(archseries)

        # For each distroseries we care about; scan for sourcepackagereleases
        # with no build associated with the distroarchserieses we're
        # interested in
        for distroseries in sorted(distroserieses,
            key=lambda x: (x.distribution, Version(x.version))):
            buildMaster.createMissingBuilds(distroseries)

        # For each build record in NEEDSBUILD, ensure it has a
        # buildqueue entry
        buildMaster.addMissingBuildQueueEntries()

        # Re-score the NEEDSBUILD properly
        buildMaster.scoreCandidates()

if __name__ == '__main__':
    script = QueueBuilder('queue-builder', dbuser=config.builddmaster.dbuser)
    script.lock_or_quit()
    try:
        script.run()
    finally:
        script.unlock()

