# Copyright 2009-2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interface for build farm job behaviours."""

__metaclass__ = type

__all__ = [
    'IBuildFarmJobBehaviour',
    ]

from zope.interface import Interface


class IBuildFarmJobBehaviour(Interface):

    def setBuilder(builder, slave):
        """Sets the associated builder and slave for this instance."""

    def logStartBuild(logger):
        """Log the start of a specific build queue item.

        The form of the log message will vary depending on the type of build.
        :param build_queue_item: A BuildQueueItem to build.
        :param logger: A logger to be used to log diagnostic information.
        """

    def composeBuildRequest(logger):
        """Compose parameters for a slave build request.

        :param logger: A logger to be used to log diagnostic information.
        :return: A tuple of (
            "builder type", `DistroArchSeries` to build against,
            {filename: `sendFileToSlave` arguments}, {extra build arguments})
        """

    def dispatchBuildToSlave(build_queue_item_id, logger):
        """Dispatch a specific build to the slave.

        :param build_queue_item_id: An identifier for the build queue item.
        :param logger: A logger to be used to log diagnostic information.
        """

    def verifyBuildRequest(logger):
        """Carry out any pre-build checks.

        :param logger: A logger to be used to log diagnostic information.
        """

    def getBuildCookie():
        """Return a string which uniquely identifies the job."""

    def verifySuccessfulBuild():
        """Check that we are allowed to collect this successful build."""

    def handleStatus(bq, status, slave_status):
        """Update the build from a WAITING slave result.

        :param bq: The `BuildQueue` currently being processed.
        :param status: The tail of the BuildStatus (eg. OK or PACKAGEFAIL).
        :param slave_status: Slave status dict from `BuilderSlave.status`.
        """
