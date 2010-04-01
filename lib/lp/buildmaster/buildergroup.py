# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Builder Group model.

Implement methods to deal with builder and their results.
"""

__metaclass__ = type

import socket
import xmlrpclib

from zope.component import getUtility

from lp.buildmaster.interfaces.builder import (
    BuildDaemonError, IBuilderSet)


class BuilderGroup:
    """Manage a set of builders based on a given architecture"""

    def commit(self):
        self._tm.commit()

    def __init__(self, logger, tm):
        self._tm = tm
        self.logger = logger

    def checkAvailableSlaves(self, arch):
        """Iter through available builder-slaves for an given architecture."""
        # Get available slaves for the context architecture.
        self.builders = getUtility(IBuilderSet).getBuildersByArch(arch)

        # Actualise the results because otherwise we get our exceptions
        # at odd times
        self.logger.debug("Initialising builders for " + arch.architecturetag)

        self.builders = set(self.builders)

        self.logger.debug("Finding XMLRPC clients for the builders")

        for builder in self.builders:
            # XXX Robert Collins 2007-05-23 bug=31546: builders that are not
            # 'ok' are not worth rechecking here for some currently
            # undocumented reason. This also relates to bug #30633.
            if builder.builderok:
                builder.updateStatus(self.logger)

        # Commit the updates made to the builders.
        self.commit()
