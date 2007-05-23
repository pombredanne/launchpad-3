#!/usr/bin/python2.4
# Copyright 2004 Canonical Ltd.  All rights reserved.
# Author: Daniel Silverstone <daniel.silverstone@canonical.com>
#         Celso Providelo <celso.providelo@canonical.com>
#
# Builder Slave Scanner and result collector

__metaclass__ = type

import _pythonpath

from zope.component import getUtility

from canonical.config import config
from canonical.buildmaster.master import (
    BuilddMaster, builddmaster_lockfilename)

from canonical.launchpad.scripts.base import (LaunchpadCronScript,
    LaunchpadScriptFailure)
from canonical.launchpad.interfaces import IDistroArchReleaseSet
from canonical.lp import READ_COMMITTED_ISOLATION


class SlaveScanner(LaunchpadCronScript):

    def main(self):
        self.logger.info("Slave Scan Process Initiated.")

        if self.args:
            raise LaunchpadScriptFailure(
                "Unhandled arguments %s" % repr(self.args))

        buildMaster = BuilddMaster(self.logger, self.txn)

        self.logger.info("Setting Builders.")
        # Put every distroarchrelease we can find into the build master.
        for archrelease in getUtility(IDistroArchReleaseSet):
            buildMaster.addDistroArchRelease(archrelease)
            buildMaster.setupBuilders(archrelease)

        self.logger.info("Scanning Builders.")
        # Scan all the pending builds, update logtails and retrieve
        # builds where they are completed
        result_code = buildMaster.scanActiveBuilders()

        # Now that the slaves are free, ask the buildmaster to calculate
        # the set of build candiates
        buildCandidatesSortedByProcessor = buildMaster.sortAndSplitByProcessor()

        self.logger.info("Dispatching Jobs.")
        # Now that we've gathered in all the builds, dispatch the pending ones
        for candidate_proc in buildCandidatesSortedByProcessor.iteritems():
            processor, buildCandidates = candidate_proc
            buildMaster.dispatchByProcessor(processor, buildCandidates)

        self.logger.info("Slave Scan Process Finished.")

    @property
    def lockfilename(self):
        """Buildd master cronscript shares the same lockfile."""
        return builddmaster_lockfilename


if __name__ == '__main__':
    script = SlaveScanner('slave-scanner', dbuser=config.builddmaster.dbuser)
    script.lock_or_quit()
    try:
        script.run(isolation=READ_COMMITTED_ISOLATION)
    finally:
        script.unlock()

