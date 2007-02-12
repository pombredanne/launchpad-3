#!/usr/bin/env python
# Copyright 2004 Canonical Ltd.  All rights reserved.
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

from sourcerer.deb.version import Version

from canonical.lp import READ_COMMITTED_ISOLATION
from canonical.config import config
from canonical.buildmaster.master import BuilddMaster

from canonical.launchpad.interfaces import IDistroArchReleaseSet
from canonical.launchpad.scripts.base import (LaunchpadScript,
    LaunchpadScriptFailure)


class QueueBuilder(LaunchpadScript):
    def add_my_options(self):
        self.parser.add_option("-N", "--dry-run", action="store_true",
                          dest="dryrun", metavar="DRY_RUN", default=False,
                          help="Whether to treat this as a dry-run or not.")

    def main(self):
        if self.args:
            raise LaunchpadScriptFailure("Unhandled arguments %r" % self.args)

        if os.path.exists("/srv/launchpad.net/ubuntu-archive/cron.daily.lock"):
            # XXX: Quick and dirty "don't start if the publisher is
            # here", we should really do this in a nicer way, kiko 2007-02-05
            sys.exit(0)

        self.txn.set_isolation_level(READ_COMMITTED_ISOLATION)

        self.logger.info("Rebuilding Build Queue.")

        if self.options.dryrun:
            # XXX: DO IT in LaunchpadScript
            # XXX cprov 20060606: i know this is evil and ugly but, right now,
            # modifying launchpad/scripts/builddmaster.py and tests would be painfully.
            pass

        self.rebuildQueue()

        if not self.options.dryrun:
            self.logger.info("Buildd Queue Rebuilt. Commiting changes")
        else:
            self.logger.debug("Dry Run, changes will not be commited.")

        self.txn.commit()

    def rebuildQueue(self):
        """Look for and initialise new build jobs."""
        buildMaster = BuilddMaster(self.logger, self.txn)

        # Simple container
        distroreleases = set()

        # For every distroarchrelease we can find; put it into the build master
        for archrelease in getUtility(IDistroArchReleaseSet):
            distroreleases.add(archrelease.distrorelease)
            buildMaster.addDistroArchRelease(archrelease)

        # For each distrorelease we care about; scan for sourcepackagereleases
        # with no build associated with the distroarchreleases we're
        # interested in
        for distrorelease in sorted(distroreleases,
            key=lambda x: (x.distribution, Version(x.version))):
            buildMaster.createMissingBuilds(distrorelease)

        # inspect depwaiting and look retry those which seems possible
        buildMaster.retryDepWaiting()

        # For each build record in NEEDSBUILD, ensure it has a
        # buildqueue entry
        buildMaster.addMissingBuildQueueEntries()

        # Re-score the NEEDSBUILD properly
        buildMaster.sanitiseAndScoreCandidates()


if __name__ == '__main__':
    # Note the use of the same lockfilename as the slave scanner.
    script = QueueBuilder('queue-builder', lockfilename='build-master',
                          dbuser=config.builddmaster.dbuser)
    script.lock_or_quit()
    script.run()
    script.unlock()

