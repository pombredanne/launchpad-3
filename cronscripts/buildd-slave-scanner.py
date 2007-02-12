#!/usr/bin/env python
# Copyright 2004 Canonical Ltd.  All rights reserved.
# Author: Daniel Silverstone <daniel.silverstone@canonical.com>
#         Celso Providelo <celso.providelo@canonical.com>
#
# Builder Slave Scanner and result collector

__metaclass__ = type

import _pythonpath

from zope.component import getUtility

from canonical.config import config
from canonical.buildmaster.master import BuilddMaster

from canonical.launchpad.scripts.base import (LaunchpadScript,
    LaunchpadScriptFailure)
from canonical.launchpad.interfaces import IDistroArchReleaseSet


class SlaveScanner(LaunchpadScript):
    def main(self):
        self.logger.info("Slave Scan Process Initiated.")

        if self.args:
            raise LaunchpadScriptFailure("Unhandled arguments %s" % repr(self.args))

        buildMaster = BuilddMaster(self.logger, self.txn)

        self.logger.info("Setting Builders.")

        # For every distroarchrelease we can find;
        # put it into the build master
        for archrelease in getUtility(IDistroArchReleaseSet):
            buildMaster.addDistroArchRelease(archrelease)
            buildMaster.setupBuilders(archrelease)

        self.logger.info("Scanning Builders.")
        # Scan all the pending builds; update logtails; retrieve
        # builds where they are compled
        result_code = buildMaster.scanActiveBuilders()

        # Now that the slaves are free, ask the buildmaster to calculate
        # the set of build candiates
        buildCandidatesSortedByProcessor = buildMaster.sortAndSplitByProcessor()

        self.logger.info("Dispatching Jobs.")
        # Now that we've gathered in all the builds;
        # dispatch the pending ones
        for processor, buildCandidates in \
                buildCandidatesSortedByProcessor.iteritems():
            buildMaster.dispatchByProcessor(processor, buildCandidates)

        self.logger.info("Slave Scan Process Finished.")


if __name__ == '__main__':
    # Note the use of the same lockfilename as the queue builder; this
    # is intentional as they are meant to lock each other out.
    script = SlaveScanner('slave-scanner', lockfilename='build-master',
                          dbuser=config.builddmaster.dbuser)
    script.lock_or_quit()
    script.run()
    script.unlock()

