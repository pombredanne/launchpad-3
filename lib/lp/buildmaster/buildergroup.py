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
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.librarian.interfaces import ILibrarianClient
from canonical.librarian.utils import copy_and_close
from lp.registry.interfaces.pocket import pocketsuffix
from lp.soyuz.interfaces.build import BuildStatus, IBuildSet
from lp.buildmaster.interfaces.builder import (
    BuildDaemonError, BuildJobMismatch, IBuilderSet)
from lp.soyuz.interfaces.buildqueue import IBuildQueueSet
from canonical.launchpad.interfaces import NotFoundError
from canonical.database.constants import UTC_NOW
from canonical.database.sqlbase import (
    flush_database_updates, clear_current_connection_cache, cursor)


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
            builder.failbuilder(str(reason))
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

    def failBuilder(self, builder, reason):
        """Mark builder as failed.

        Set builderok as False, store the reason in failnotes.
        """
        # XXX cprov 2007-04-17: ideally we should be able to notify the
        # the buildd-admins about FAILED builders. One alternative is to
        # make the buildd_cronscript (slave-scanner, in this case) to exit
        # with error, for those cases buildd-sequencer automatically sends
        # an email to admins with the script output.
        builder.failbuilder(reason)

    def updateBuild(self, queueItem):
        """Verify the current build job status.

        Perform the required actions for each state.
        """
        try:
            slave_status = queueItem.builder.slaveStatus()

        except (xmlrpclib.Fault, socket.error), info:
            # XXX cprov 2005-06-29:
            # Hmm, a problem with the xmlrpc interface,
            # disable the builder ?? or simple notice the failure
            # with a timestamp.
            info = ("Could not contact the builder %s, caught a (%s)"
                    % (queueItem.builder.url, info))
            self.logger.debug(info, exc_info=True)
            # keep the job for scan
            return

        builder_status_handlers = {
            'BuilderStatus.IDLE': queueItem.updateBuild_IDLE,
            'BuilderStatus.BUILDING': queueItem.updateBuild_BUILDING,
            'BuilderStatus.ABORTING': queueItem.updateBuild_ABORTING,
            'BuilderStatus.ABORTED': queueItem.updateBuild_ABORTED,
            'BuilderStatus.WAITING': self.updateBuild_WAITING,
            }

        builder_status = slave_status['builder_status']
        if builder_status not in builder_status_handlers:
            self.logger.critical(
                "Builder on %s returned unknown status %s, failing it"
                % (queueItem.builder.url, builder_status))
            self.failBuilder(
                queueItem.builder,
                "Unknown status code (%s) returned from status() probe."
                % builder_status)
            queueItem.builder = None
            queueItem.setDateStarted(None)
            self.commit()
            return

        # Since logtail is a xmlrpclib.Binary container and it is returned
        # from the IBuilder content class, it arrives protected by a Zope
        # Security Proxy, which is not declared, thus empty. Before passing
        # it to the status handlers we will simply remove the proxy.
        logtail = removeSecurityProxy(slave_status.get('logtail'))
        build_id = slave_status.get('build_id')
        build_status = slave_status.get('build_status')
        filemap = slave_status.get('filemap')
        dependencies = slave_status.get('dependencies')

        method = builder_status_handlers[builder_status]
        try:
            # XXX cprov 2007-05-25: We need this code for WAITING status
            # handler only until we are able to also move it to
            # BuildQueue content class and avoid to pass 'queueItem'.
            if builder_status == 'BuilderStatus.WAITING':
                method(queueItem, slave_status, logtail, self.logger)
            else:
                method(build_id, build_status, logtail,
                       filemap, dependencies, self.logger)
        except TypeError, e:
            self.logger.critical("Received wrong number of args in response.")
            self.logger.exception(e)

        self.commit()

    def updateBuild_WAITING(self, queueItem, slave_status, logtail, logger):
        """Perform the actions needed for a slave in a WAITING state

        Buildslave can be WAITING in five situations:

        * Build has failed, no filemap is received (PACKAGEFAIL, DEPFAIL,
                                                    CHROOTFAIL, BUILDERFAIL)

        * Build has been built successfully (BuildStatus.OK), in this case
          we have a 'filemap', so we can retrieve those files and store in
          Librarian with getFileFromSlave() and then pass the binaries to
          the uploader for processing.
        """
        librarian = getUtility(ILibrarianClient)
        build_status = slave_status['build_status']

        # XXX: dsilvers 2005-03-02: Confirm the builder has the right build?
        assert build_status.startswith('BuildStatus.'), (
            'Malformed status string: %s' % build_status)

        build_status = build_status[len('BuildStatus.'):]
        # XXX: wgrant 2009-01-13: build is not part of IBuildFarmJob,
        # but this method will move and be fixed before any other job
        # types come into use.
        queueItem.specific_job.build.handleStatus(
            build_status, librarian, slave_status)
