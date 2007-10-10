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
#XXX: Only needed until the soyuz buildmaster class is fully deleted.
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.buildmaster.master import (
    BuilddMaster, builddmaster_lockfilename)

from canonical.launchpad.scripts.base import (LaunchpadCronScript,
    LaunchpadScriptFailure)
from canonical.launchpad.interfaces import IBuilderSet
from canonical.lp import READ_COMMITTED_ISOLATION


class SlaveScanner(LaunchpadCronScript):

    def main(self):
        if self.args:
            raise LaunchpadScriptFailure(
                "Unhandled arguments %s" % repr(self.args))

        builder_set = getUtility(IBuilderSet)
        buildMaster = builder_set.pollBuilders(self.logger, self.txn)
        # XXX: lifeless 2007-05-25:
        # Only needed until the soyuz buildmaster class is fully deleted.
        builder_set.dispatchBuilds(self.logger, removeSecurityProxy(buildMaster))

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

