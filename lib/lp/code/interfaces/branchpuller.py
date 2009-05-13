# Copyright 2009 Canonical Ltd.  All rights reserved.

"""The public interface to the model of the branch puller."""

__metaclass__ = type
__all__ = [
    'IBranchPuller',
    ]


from zope.interface import Attribute, Interface


class IBranchPuller(Interface):
    """The interface to the database for the branch puller."""

    MAXIMUM_MIRROR_FAILURES = Attribute(
        "The maximum number of failures before we disable mirroring.")

    MIRROR_TIME_INCREMENT = Attribute(
        "How frequently we mirror branches.")

    def getPullQueue(branch_type):
        """Return a queue of branches to mirror using the puller.

        :param branch_type: A value from the `BranchType` enum.
        """

    def acquireBranchToPull():
        """Return a Branch to pull and mark it as mirror-started.

        :return: The branch object to pull next, or ``None`` if there is no
            branch to pull.
        """
