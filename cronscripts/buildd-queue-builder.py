#!/usr/bin/python2.4
# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# Author: Daniel Silverstone <daniel.silverstone@canonical.com>
#         Celso Providelo <celso.providelo@canonical.com>
#
# Build Jobs initialisation
#
__metaclass__ = type

import _pythonpath
import os
import sys

from zope.component import getUtility

from canonical.archivepublisher.debversion import Version
from canonical.lp import READ_COMMITTED_ISOLATION
from canonical.config import config
from canonical.buildmaster.master import (
    BuilddMaster, builddmaster_lockfilename)

from canonical.launchpad.interfaces import IDistroArchSeriesSet
from canonical.launchpad.scripts.base import (LaunchpadCronScript,
    LaunchpadScriptFailure)


class QueueBuilder(LaunchpadCronScript):

    def add_my_options(self):
        self.parser.add_option(
            "-n", "--dry-run", action="store_true",
            dest="dryrun", metavar="DRY_RUN", default=False,
            help="Whether to treat this as a dry-run or not.")

    def lock_or_quit(self):
        """Redefine lock_or_quit to check cron.daily lockfile.

        If it finds the cron.daily lockfile it should simply exit quietly.
        We don't want to run queue-builder simultaneously with the cron.daily
        because it might be a huge source of mistakes, but in the same way we
        don't want to recieve email warnings (buildd-sequencer) for this event.
        """
        if os.path.exists(config.builddmaster.crondaily_lockfile):
            sys.exit(0)

        LaunchpadCronScript.lock_or_quit(self)

    def main(self):
        """Invoke rebuildQueue.

        Check if the cron.daily is running, quietly exits if true.
        Force isolation level to READ_COMMITTED_ISOLATION.
        Deals with the current transaction according the dry-run option.
        """
        if self.args:
            raise LaunchpadScriptFailure("Unhandled arguments %r" % self.args)

        if self.options.dryrun:
            self.logger.info("Dry run: changes will not be committed.")
            self.txn = _FakeZTM()

        self.rebuildQueue()
        self.txn.commit()

    def rebuildQueue(self):
        """Look for and initialise new build jobs."""

        self.logger.info("Rebuilding Build Queue.")

        # XXX cprov 2007-03-21: In order to avoid the partial commits inside
        # BuilddMaster to happen we pass a FakeZtm instance
        class _FakeZTM:
            """A fake transaction manager."""
            def commit(self):
                pass

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

        # Inspect depwaiting and look retry those which seems possible
        buildMaster.retryDepWaiting()

        # For each build record in NEEDSBUILD, ensure it has a
        # buildqueue entry
        buildMaster.addMissingBuildQueueEntries()

        # Re-score the NEEDSBUILD properly
        buildMaster.sanitiseAndScoreCandidates()

    @property
    def lockfilename(self):
        """Buildd master cronscript shares the same lockfile."""
        return builddmaster_lockfilename


if __name__ == '__main__':
    script = QueueBuilder('queue-builder', dbuser=config.builddmaster.dbuser)
    script.lock_or_quit()
    try:
        script.run(isolation=READ_COMMITTED_ISOLATION)
    finally:
        script.unlock()

