# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Interface for build farm job behaviors."""

__metaclass__ = type

__all__ = [
    'BuildBehaviorMismatch',
    'IBuildFarmJobBehavior',
    ]

from zope.interface import Interface


class BuildBehaviorMismatch(Exception):
    """
    A general exception that can be raised when the builder's current behavior
    does not match the expected behavior.
    """


class IBuildFarmJobBehavior(Interface):

    def setBuilder(builder):
        """Sets the associated builder reference for this instance."""

    def logStartBuild(logger):
        """Log the start of a specific build queue item.

        The form of the log message will vary depending on the type of build.
        :param build_queue_item: A BuildQueueItem to build.
        :param logger: A logger to be used to log diagnostic information.
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

    def slaveStatus(raw_slave_status, status):
        """Return a dict of custom slave status values for this behavior.

        :param raw_slave_status: The value returned by the build slave's
           status() method.
        :param status: A dict of the processed slave status values provided
           by all types: builder_status, build_id, and optionally build_status
           or logtail.
        :return: a dict of the processed status information, including any
            provided values.
        """

    def verifySlaveBuildID(slave_build_id):
        """Verify that a slave's build ID shows no signs of corruption.

        :param slave_build_id: The slave's build ID, as specified in
           dispatchBuildToSlave.
        :raises CorruptBuildID: if the build ID is determined to be corrupt.
        """

    def updateBuild(queueItem):
        """Verify the current build job status.

        Perform the required actions for each state.
        """

