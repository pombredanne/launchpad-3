# Copyright 2009 Canonical Ltd.  This software is licensed under the
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

    def slaveStatus(raw_slave_status):
        """Return a dict of custom slave status values for this behavior.

        :param raw_slave_status: The value returned by the build slave's
           status() method.
        :return: a dict of extra key/values to be included in the result
            of IBuilder.slaveStatus().
        """
