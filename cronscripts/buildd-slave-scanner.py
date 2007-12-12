#!/usr/bin/python2.4
# Copyright 2004 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0403
# Author: Daniel Silverstone <daniel.silverstone@canonical.com>
#         Celso Providelo <celso.providelo@canonical.com>
#
# Builder Slave Scanner and result collector

__metaclass__ = type

import _pythonpath

from zope.component import getUtility

from canonical.config import config
from canonical.launchpad.scripts.base import (
    LaunchpadCronScript, LaunchpadScriptFailure)
from canonical.launchpad.interfaces import IBuilderSet


class SlaveScanner(LaunchpadCronScript):

    def main(self):
        if self.args:
            raise LaunchpadScriptFailure(
                "Unhandled arguments %s" % repr(self.args))

        builder_set = getUtility(IBuilderSet)
        buildMaster = builder_set.pollBuilders(self.logger, self.txn)

        self.logger.info("Dispatching Jobs.")

        for builder in builder_set:
            self.logger.info("Processing: %s" % builder.name)
            # XXX cprov 20071109: we don't support manual dispatching
            # yet. Once we support it this clause should be removed.
            if builder.manual:
                self.logger.warn('builder is in manual state. Ignored.')
                continue
            if not builder.is_available:
                self.logger.warn('builder is not available. Ignored.')
                continue
            candidate = builder.findBuildCandidate()
            if candidate is None:
                self.logger.debug(
                    "No candidates available for builder.")
                continue
            builder.dispatchBuildCandidate(candidate)
            self.txn.commit()

        self.logger.info("Slave Scan Process Finished.")

if __name__ == '__main__':
    script = SlaveScanner('slave-scanner', dbuser=config.builddmaster.dbuser)
    script.lock_or_quit()
    try:
        script.run()
    finally:
        script.unlock()

