# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Common build base classes."""

__metaclass__ = type

__all__ = ['BuildBase']

import datetime
import logging
import pytz

from lp.soyuz.interfaces.build import BuildStatus
from canonical.database.constants import UTC_NOW

class BuildBase:
    def handleStatus(self, status, queueItem, librarian, slave_status):
        """See `IBuildBase`."""
        # XXX: queueItem should be gettable from self?
        logger = logging.getLogger()

        method = getattr(self, '_handleStatus_' + status, None)

        if method is None:
            logger.critical("Unknown BuildStatus '%s' for builder '%s'"
                            % (status, queueItem.builder.url))
            return

        method(queueItem, librarian, slave_status, logger)

    def _handleStatus_OK(self, queueItem, librarian, slave_status, logger):
        """Handle a package that built successfully."""
        raise NotImplementedError()

    def _handleStatus_PACKAGEFAIL(self, queueItem, librarian, slave_status,
                                  logger):
        """Handle a package that had failed to build.

        Build has failed when trying the work with the target package,
        set the job status as FAILEDTOBUILD, store available info and
        remove Buildqueue entry.
        """
        self.buildstate = BuildStatus.FAILEDTOBUILD
        self.storeBuildInfo(queueItem, librarian, slave_status)
        queueItem.builder.cleanSlave()
        self.notify()
        queueItem.destroySelf()

    def _handleStatus_DEPFAIL(self, queueItem, librarian, slave_status,
                              logger):
        """Handle a package that had missing dependencies.

        Build has failed by missing dependencies, set the job status as
        MANUALDEPWAIT, store available information, remove BuildQueue
        entry and release builder slave for another job.
        """
        self.buildstate = BuildStatus.MANUALDEPWAIT
        self.storeBuildInfo(queueItem, librarian, slave_status)
        logger.critical("***** %s is MANUALDEPWAIT *****"
                        % queueItem.builder.name)
        queueItem.builder.cleanSlave()
        queueItem.destroySelf()

    def _handleStatus_CHROOTFAIL(self, queueItem, librarian, slave_status,
                                 logger):
        """Handle a package that had failed when unpacking the CHROOT.

        Build has failed when installing the current CHROOT, mark the
        job as CHROOTFAIL, store available information, remove BuildQueue
        and release the builder.
        """
        self.buildstate = BuildStatus.CHROOTWAIT
        self.storeBuildInfo(queueItem, librarian, slave_status)
        logger.critical("***** %s is CHROOTWAIT *****" %
                        queueItem.builder.name)
        queueItem.builder.cleanSlave()
        self.notify()
        queueItem.destroySelf()

    def _handleStatus_BUILDERFAIL(self, queueItem, librarian, slave_status,
                                  logger):
        """Handle builder failures.

        Build has been failed when trying to build the target package,
        The environment is working well, so mark the job as NEEDSBUILD again
        and 'clean' the builder to do another jobs.
        """
        logger.warning("***** %s has failed *****"
                       % queueItem.builder.name)
        queueItem.builder.failbuilder(
            "Builder returned BUILDERFAIL when asked for its status")
        # simply reset job
        self.storeBuildInfo(queueItem, librarian, slave_status)
        queueItem.reset()

    def _handleStatus_GIVENBACK(self, queueItem, librarian, slave_status,
                                logger):
        """Handle automatic retry requested by builder.

        GIVENBACK pseudo-state represents a request for automatic retry
        later, the build records is delayed by reducing the lastscore to
        ZERO.
        """
        logger.warning("***** %s is GIVENBACK by %s *****"
                       % (slave_status['build_id'], queueItem.builder.name))
        self.storeBuildInfo(queueItem, librarian, slave_status)
        # XXX cprov 2006-05-30: Currently this information is not
        # properly presented in the Web UI. We will discuss it in
        # the next Paris Summit, infinity has some ideas about how
        # to use this content. For now we just ensure it's stored.
        queueItem.builder.cleanSlave()
        queueItem.reset()

    def getLogFromSlave(self, queueItem):
        """See `IBuildBase`."""
        return queueItem.builder.transferSlaveFileToLibrarian(
            'buildlog', queueItem.getLogFileName(),
            self.is_private)

    def storeBuildInfo(self, queueItem, librarian, slave_status):
        """See `IBuildBase`."""
        self.buildlog = self.getLogFromSlave(queueItem)
        self.builder = queueItem.builder
        # XXX cprov 20060615 bug=120584: Currently buildduration includes
        # the scanner latency, it should really be asking the slave for
        # the duration spent building locally.
        self.datebuilt = UTC_NOW
        # We need dynamic datetime.now() instance to be able to perform
        # the time operations for duration.
        RIGHT_NOW = datetime.datetime.now(pytz.timezone('UTC'))
        self.buildduration = RIGHT_NOW - queueItem.date_started
