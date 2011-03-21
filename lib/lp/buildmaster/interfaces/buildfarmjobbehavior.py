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

    def updateSlaveStatus(raw_slave_status, status):
        """Update the slave status dict with custom values for this behavior.

        :param raw_slave_status: The value returned by the build slave's
           status() method.
        :param status: A dict of the processed slave status values provided
           by all types: builder_status, build_id, and optionally build_status
           or logtail. This should have any behaviour-specific values
           added to it.
        """

    def verifySlaveBuildCookie(slave_build_cookie):
        """Verify that a slave's build cookie shows no signs of corruption.

        :param slave_build_cookie: The slave's build cookie, as specified in
           `dispatchBuildToSlave`.
        :raises CorruptBuildCookie: if the build cookie isn't what it's
            supposed to be.
        """

    def updateBuild(queueItem):
        """Verify the current build job status.

        Perform the required actions for each state.

        :param queueItem: The `BuildQueue` for the build.
        :return: A Deferred that fires when the update is done.
        """

