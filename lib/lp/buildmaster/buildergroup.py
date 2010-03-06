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
                self.updateBuilderStatus(builder, arch)

        # Commit the updates made to the builders.
        self.commit()

    def updateBuilderStatus(self, builder, arch):
        """Update the status for a builder by probing it.

        :param builder: A builder object.
        :param arch: The expected architecture family of the builder.
        """
        self.logger.debug('Checking %s' % builder.name)
        try:
            builder.checkSlaveAlive()
            builder.checkCanBuildForDistroArchSeries(arch)
            builder.rescueIfLost(self.logger)
        # Catch only known exceptions.
        # XXX cprov 2007-06-15 bug=120571: ValueError & TypeError catching is
        # disturbing in this context. We should spend sometime sanitizing the
        # exceptions raised in the Builder API since we already started the
        # main refactoring of this area.
        except (ValueError, TypeError, xmlrpclib.Fault,
                BuildDaemonError), reason:
            builder.failBuilder(str(reason))
            self.logger.warn(
                "%s (%s) marked as failed due to: %s",
                builder.name, builder.url, builder.failnotes, exc_info=True)
        except socket.error, reason:
            error_message = str(reason)
            builder.handleTimeout(self.logger, error_message)
