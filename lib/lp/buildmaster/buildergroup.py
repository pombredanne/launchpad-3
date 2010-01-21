# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Builder Group model.

Implement methods to deal with builder and their results.
"""

__metaclass__ = type

import socket
import xmlrpclib

from sqlobject import SQLObjectNotFound

from zope.component import getUtility

from lp.soyuz.interfaces.build import IBuildSet
from lp.buildmaster.interfaces.builder import (
    BuildDaemonError, BuildJobMismatch, IBuilderSet)
from lp.soyuz.interfaces.buildqueue import IBuildQueueSet
from canonical.launchpad.interfaces import NotFoundError


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
            self.rescueBuilderIfLost(builder)
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

    def rescueBuilderIfLost(self, builder):
        """Reset Builder slave if job information doesn't match with DB.

        If builder is BUILDING or WAITING but has an information record
        that doesn't match what is stored in the DB, we have to dismiss
        its current actions and let the slave free for another job,
        assuming the XMLRPC is working properly at this point.
        """
        status_sentence = builder.slaveStatusSentence()

        # 'ident_position' dict relates the position of the job identifier
        # token in the sentence received from status(), according the
        # two status we care about. See see lib/canonical/buildd/slave.py
        # for further information about sentence format.
        ident_position = {
            'BuilderStatus.BUILDING': 1,
            'BuilderStatus.WAITING': 2
            }

        # Isolate the BuilderStatus string, always the first token in
        # see lib/canonical/buildd/slave.py and
        # IBuilder.slaveStatusSentence().
        status = status_sentence[0]

        # If slave is not building nor waiting, it's not in need of rescuing.
        if status not in ident_position.keys():
            return

        # Extract information from the identifier.
        build_id, queue_item_id = status_sentence[
            ident_position[status]].split('-')

        # Check if build_id and queue_item_id exist.
        try:
            build = getUtility(IBuildSet).getByBuildID(int(build_id))
            queue_item = getUtility(IBuildQueueSet).get(int(queue_item_id))
            queued_build = getUtility(IBuildSet).getByQueueEntry(queue_item)
            # Also check whether build and buildqueue are properly related.
            if queued_build.id != build.id:
                raise BuildJobMismatch('Job build entry mismatch')

        except (SQLObjectNotFound, NotFoundError, BuildJobMismatch), reason:
            if status == 'BuilderStatus.WAITING':
                builder.cleanSlave()
            else:
                builder.requestAbort()
            self.logger.warn("Builder '%s' rescued from '%s-%s: %s'" % (
                builder.name, build_id, queue_item_id, reason))

    def updateBuild(self, queueItem):
        """Verify the current build job status.

        Perform the required actions for each state.
        """
        queueItem.builder.updateBuild(queueItem)
        self.commit()
