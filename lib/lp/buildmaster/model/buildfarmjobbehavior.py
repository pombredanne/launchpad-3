# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Base and idle BuildFarmJobBehavior classes."""

__metaclass__ = type

__all__ = [
    'BuildFarmJobBehaviorBase',
    'IdleBuildBehavior'
    ]

import logging
import socket
import xmlrpclib

from zope.component import getUtility
from zope.interface import implements
from zope.security.proxy import removeSecurityProxy

from canonical.librarian.interfaces import ILibrarianClient
from lp.buildmaster.interfaces.buildfarmjobbehavior import (
    BuildBehaviorMismatch, IBuildFarmJobBehavior)


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
                    % (self.url, info))
            logger.debug(info, exc_info=True)
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
                method(queueItem, slave_status, logtail, logger)
            else:
                method(build_id, build_status, logtail,
                       filemap, dependencies, logger)
        except TypeError, e:
            logger.critical("Received wrong number of args in response.")
            logger.exception(e)

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
