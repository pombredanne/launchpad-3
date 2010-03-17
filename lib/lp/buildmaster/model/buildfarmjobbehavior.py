# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
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

from sqlobject import SQLObjectNotFound

from zope.component import getUtility
from zope.interface import implements
from zope.security.proxy import removeSecurityProxy, isinstance as zisinstance

from canonical import encoding
from canonical.librarian.interfaces import ILibrarianClient

from canonical.launchpad.webapp.interfaces import NotFoundError
from lp.buildmaster.interfaces.builder import CorruptBuildID
from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    BuildBehaviorMismatch, IBuildFarmJobBehavior)
from lp.buildmaster.interfaces.buildqueue import IBuildQueueSet
from lp.buildmaster.model.buildqueue import BuildQueue
from lp.services.job.interfaces.job import JobStatus
from lp.soyuz.interfaces.build import IBuildSet


class BuildFarmJobBehaviorBase:
    """Ensures that all behaviors inherit the same initialisation.

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

    def slaveStatus(self, raw_slave_status):
        """See `IBuildFarmJobBehavior`.

        The default behavior is that we don't add any extra values."""
        return {}

    def _helpVerifyBuildIDComponent(self, raw_id, item_type, finder):
        """Helper for verifying parts of a `BuildFarmJob` name.

        Different `IBuildFarmJob` implementations can have different
        ways of constructing their identifying names.  The names are
        produced by `IBuildFarmJob.getName` and verified by
        `IBuildFarmJobBehavior.verifySlaveBuildID`.

        This little helper makes it easier to verify an object id
        embedded in that name, check that it's a valid number, and
        retrieve the associated database object.

        :param raw_id: An unverified id string as extracted from the
            build name.  The method will verify that it is a number, and
            try to retrieve the associated object.
        :param item_type: The type of object this id represents.  Should
            be a class.
        :param finder: A function that, given an integral id, finds the
            associated object of type `item_type`.
        :raise CorruptBuildID: If `raw_id` is malformed in some way or
            the associated `item_type` object is not found.
        :return: An object that is an instance of `item_type`.
        """
        type_name = item_type.__name__
        try:
            numeric_id = int(raw_id)
        except ValueError:
            raise CorruptBuildID(
                "%s ID is not a number: '%s'" % (type_name, raw_id))

        try:
            item = finder(numeric_id)
        except (NotFoundError, SQLObjectNotFound), reason:
            raise CorruptBuildID(
                "%s %d is not available: %s" % (
                    type_name, numeric_id, reason))
        except Exception, reason:
            raise CorruptBuildID(
                "Error while looking up %s %d: %s" % (
                    type_name, numeric_id, reason))

        if item is None:
            raise CorruptBuildID("There is no %s with id %d." % (
                type_name, numeric_id))

        assert zisinstance(item, item_type), (
            "Looked for %s, but found %s." % (type_name, repr(item)))

        return item

    def getVerifiedBuild(self, raw_id):
        """Verify and retrieve the `Build` component of a slave build id.

        This does part of the verification for `verifySlaveBuildID`.

        By default, a `BuildFarmJob` has an identifying name of the form
        "b-q", where b is the id of its `Build` and q is the id of its
        `BuildQueue` record.

        Use `getVerifiedBuild` to verify the "b" part, and retrieve the
        associated `Build`.
        """
        # Avoid circular import.
        from lp.soyuz.model.build import Build

        return self._helpVerifyBuildIDComponent(
            raw_id, Build, getUtility(IBuildSet).getByBuildID)

    def getVerifiedBuildQueue(self, raw_id):
        """Verify and retrieve the `BuildQueue` component of a slave build id.

        This does part of the verification for `verifySlaveBuildID`.

        By default, a `BuildFarmJob` has an identifying name of the form
        "b-q", where b is the id of its `Build` and q is the id of its
        `BuildQueue` record.

        Use `getVerifiedBuildQueue` to verify the "q" part, and retrieve
        the associated `BuildQueue` object.
        """
        return self._helpVerifyBuildIDComponent(
            raw_id, BuildQueue, getUtility(IBuildQueueSet).get)

    def verifySlaveBuildID(self, slave_build_id):
        """See `IBuildFarmJobBehavior`."""
        # Extract information from the identifier.
        try:
            build_id, queue_item_id = slave_build_id.split('-')
        except ValueError:
            raise CorruptBuildID('Malformed build ID')
            
        build = self.getVerifiedBuild(build_id)
        queue_item = self.getVerifiedBuildQueue(queue_item_id)

        if build != queue_item.specific_job.build:
            raise CorruptBuildID('Job build entry mismatch')

    def updateBuild(self, queueItem):
        """See `IBuildFarmJobBehavior`."""
        logger = logging.getLogger('slave-scanner')

        try:
            slave_status = self._builder.slaveStatus()
        except (xmlrpclib.Fault, socket.error), info:
            # XXX cprov 2005-06-29:
            # Hmm, a problem with the xmlrpc interface,
            # disable the builder ?? or simple notice the failure
            # with a timestamp.
            info = ("Could not contact the builder %s, caught a (%s)"
                    % (queueItem.builder.url, info))
            logger.debug(info, exc_info=True)
            # keep the job for scan
            return

        builder_status_handlers = {
            'BuilderStatus.IDLE': self.updateBuild_IDLE,
            'BuilderStatus.BUILDING': self.updateBuild_BUILDING,
            'BuilderStatus.ABORTING': self.updateBuild_ABORTING,
            'BuilderStatus.ABORTED': self.updateBuild_ABORTED,
            'BuilderStatus.WAITING': self.updateBuild_WAITING,
            }

        builder_status = slave_status['builder_status']
        if builder_status not in builder_status_handlers:
            logger.critical(
                "Builder on %s returned unknown status %s, failing it"
                % (self._builder.url, builder_status))
            self._builder.failBuilder(
                "Unknown status code (%s) returned from status() probe."
                % builder_status)
            # XXX: This will leave the build and job in a bad state, but
            # should never be possible, since our builder statuses are
            # known.
            queueItem._builder = None
            queueItem.setDateStarted(None)
            return

        # Since logtail is a xmlrpclib.Binary container and it is returned
        # from the IBuilder content class, it arrives protected by a Zope
        # Security Proxy, which is not declared, thus empty. Before passing
        # it to the status handlers we will simply remove the proxy.
        logtail = removeSecurityProxy(slave_status.get('logtail'))

        method = builder_status_handlers[builder_status]
        try:
            method(queueItem, slave_status, logtail, logger)
        except TypeError, e:
            logger.critical("Received wrong number of args in response.")
            logger.exception(e)

    def updateBuild_IDLE(self, queueItem, slave_status, logtail, logger):
        """Somehow the builder forgot about the build job.

        Log this and reset the record.
        """
        logger.warn(
            "Builder %s forgot about buildqueue %d -- resetting buildqueue "
            "record" % (queueItem.builder.url, queueItem.id))
        queueItem.reset()

    def updateBuild_BUILDING(self, queueItem, slave_status, logtail, logger):
        """Build still building, collect the logtail"""
        if queueItem.job.status != JobStatus.RUNNING:
            queueItem.job.start()
        queueItem.logtail = encoding.guess(str(logtail))

    def updateBuild_ABORTING(self, queueItem, slave_status, logtail, logger):
        """Build was ABORTED.

        Master-side should wait until the slave finish the process correctly.
        """
        queueItem.logtail = "Waiting for slave process to be terminated"

    def updateBuild_ABORTED(self, queueItem, slave_status, logtail, logger):
        """ABORTING process has successfully terminated.

        Clean the builder for another jobs.
        """
        queueItem.builder.cleanSlave()
        queueItem.builder = None
        if queueItem.job.status != JobStatus.FAILED:
            queueItem.job.fail()
        queueItem.specific_job.jobAborted()

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

        queueItem.specific_job.build.handleStatus(
            build_status, librarian, slave_status)


class IdleBuildBehavior(BuildFarmJobBehaviorBase):

    implements(IBuildFarmJobBehavior)

    def __init__(self):
        """The idle behavior is special in that a buildfarmjob is not
        specified during initialisation as it is not the result of an
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

    def verifySlaveBuildID(self, slave_build_id):
        """See `IBuildFarmJobBehavior`."""
        raise CorruptBuildID('No job assigned to builder')
