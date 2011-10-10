# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Base and idle BuildFarmJobBehavior classes."""

__metaclass__ = type

__all__ = [
    'BuildFarmJobBehaviorBase',
    'IdleBuildBehavior',
    ]

import logging
import socket
import xmlrpclib

import transaction
from twisted.internet import defer
from zope.component import getUtility
from zope.interface import implements
from zope.security.proxy import removeSecurityProxy

from canonical.librarian.interfaces import ILibrarianClient
from lp.buildmaster.interfaces.builder import (
    BuildSlaveFailure,
    CorruptBuildCookie,
    )
from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    BuildBehaviorMismatch,
    IBuildFarmJobBehavior,
    )
from lp.services import encoding
from lp.services.database.transaction_policy import DatabaseTransactionPolicy
from lp.services.job.interfaces.job import JobStatus


class BuildFarmJobBehaviorBase:
    """Ensures that all behaviors inherit the same initialization.

    All build-farm job behaviors should inherit from this.
    """

    def __init__(self, buildfarmjob):
        """Store a reference to the job_type with which we were created."""
        self.buildfarmjob = buildfarmjob
        self._builder = None

    @property
    def build(self):
        return self.buildfarmjob.build

    def setBuilder(self, builder):
        """The builder should be set once and not changed."""
        self._builder = builder

    def verifyBuildRequest(self, logger):
        """The default behavior is a no-op."""
        pass

    def updateSlaveStatus(self, raw_slave_status, status):
        """See `IBuildFarmJobBehavior`.

        The default behavior is that we don't add any extra values."""
        pass

    def verifySlaveBuildCookie(self, slave_build_cookie):
        """See `IBuildFarmJobBehavior`."""
        expected_cookie = self.buildfarmjob.generateSlaveBuildCookie()
        if slave_build_cookie != expected_cookie:
            raise CorruptBuildCookie("Invalid slave build cookie.")

    def updateBuild(self, queueItem):
        """See `IBuildFarmJobBehavior`."""
        logger = logging.getLogger('slave-scanner')

        d = self._builder.slaveStatus()

        def got_failure(failure):
            failure.trap(xmlrpclib.Fault, socket.error)
            info = failure.value
            info = ("Could not contact the builder %s, caught a (%s)"
                    % (queueItem.builder.url, info))
            raise BuildSlaveFailure(info)

        def got_status(slave_status):
            builder_status_handlers = {
                'BuilderStatus.IDLE': self.updateBuild_IDLE,
                'BuilderStatus.BUILDING': self.updateBuild_BUILDING,
                'BuilderStatus.ABORTING': self.updateBuild_ABORTING,
                'BuilderStatus.ABORTED': self.updateBuild_ABORTED,
                'BuilderStatus.WAITING': self.updateBuild_WAITING,
                }

            builder_status = slave_status['builder_status']
            if builder_status not in builder_status_handlers:
                transaction.commit()
                with DatabaseTransactionPolicy(read_only=False):
                    logger.critical(
                        "Builder on %s returned unknown status %s; "
                        "failing it."
                        % (self._builder.url, builder_status))
                    self._builder.failBuilder(
                        "Unknown status code (%s) returned from status() "
                        "probe."
                        % builder_status)
                    # XXX: This will leave the build and job in a bad
                    # state, but should never be possible since our
                    # builder statuses are known.
                    queueItem._builder = None
                    queueItem.setDateStarted(None)
                    transaction.commit()
                return

            # Since logtail is a xmlrpclib.Binary container and it is
            # returned from the IBuilder content class, it arrives
            # protected by a Zope Security Proxy, which is not declared,
            # thus empty. Before passing it to the status handlers we
            # will simply remove the proxy.
            logtail = removeSecurityProxy(slave_status.get('logtail'))

            method = builder_status_handlers[builder_status]
            return defer.maybeDeferred(
                method, queueItem, slave_status, logtail, logger)

        d.addErrback(got_failure)
        d.addCallback(got_status)
        return d

    def updateBuild_IDLE(self, queueItem, slave_status, logtail, logger):
        """Somehow the builder forgot about the build job.

        Log this and reset the record.
        """
        logger.warn(
            "Builder %s forgot about buildqueue %d -- resetting buildqueue "
            "record" % (queueItem.builder.url, queueItem.id))
        transaction.commit()
        with DatabaseTransactionPolicy(read_only=False):
            queueItem.reset()
            transaction.commit()

    def updateBuild_BUILDING(self, queueItem, slave_status, logtail, logger):
        """Build still building, collect the logtail"""
        transaction.commit()
        with DatabaseTransactionPolicy(read_only=False):
            if queueItem.job.status != JobStatus.RUNNING:
                queueItem.job.start()
            queueItem.logtail = encoding.guess(str(logtail))
            transaction.commit()

    def updateBuild_ABORTING(self, queueItem, slave_status, logtail, logger):
        """Build was ABORTED.

        Master-side should wait until the slave finish the process correctly.
        """
        transaction.commit()
        with DatabaseTransactionPolicy(read_only=False):
            queueItem.logtail = "Waiting for slave process to be terminated"
            transaction.commit()

    def updateBuild_ABORTED(self, queueItem, slave_status, logtail, logger):
        """ABORTING process has successfully terminated.

        Clean the builder for another jobs.
        """
        d = queueItem.builder.cleanSlave()

        def got_cleaned(ignored):
            transaction.commit()
            with DatabaseTransactionPolicy(read_only=False):
                queueItem.builder = None
                if queueItem.job.status != JobStatus.FAILED:
                    queueItem.job.fail()
                queueItem.specific_job.jobAborted()
                transaction.commit()
        return d.addCallback(got_cleaned)

    def extractBuildStatus(self, slave_status):
        """Read build status name.

        :param slave_status: build status dict as passed to the
            updateBuild_* methods.
        :return: the unqualified status name, e.g. "OK".
        """
        status_string = slave_status['build_status']
        lead_string = 'BuildStatus.'
        assert status_string.startswith(lead_string), (
            "Malformed status string: '%s'" % status_string)

        return status_string[len(lead_string):]

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
        build_status = self.extractBuildStatus(slave_status)

        # XXX: dsilvers 2005-03-02: Confirm the builder has the right build?

        build = queueItem.specific_job.build
        d = build.handleStatus(build_status, librarian, slave_status)
        return d


class IdleBuildBehavior(BuildFarmJobBehaviorBase):

    implements(IBuildFarmJobBehavior)

    def __init__(self):
        """The idle behavior is special in that a buildfarmjob is not
        specified during initialization as it is not the result of an
        adaption.
        """
        super(IdleBuildBehavior, self).__init__(None)

    def logStartBuild(self, logger):
        """See `IBuildFarmJobBehavior`."""
        raise BuildBehaviorMismatch(
            "Builder was idle when asked to log the start of a build.")

    def dispatchBuildToSlave(self, build_queue_item_id, logger):
        """See `IBuildFarmJobBehavior`."""
        raise BuildBehaviorMismatch(
            "Builder was idle when asked to dispatch a build to the slave.")

    @property
    def status(self):
        """See `IBuildFarmJobBehavior`."""
        return "Idle"

    def verifySlaveBuildCookie(self, slave_build_id):
        """See `IBuildFarmJobBehavior`."""
        raise CorruptBuildCookie('No job assigned to builder')
