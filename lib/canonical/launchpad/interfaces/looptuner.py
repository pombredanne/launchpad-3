# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

"""Interface for loop bodies that can be fed to the LoopTuner."""

__metaclass__ = type
__all__ = ['ITunableLoop']

from zope.interface import Interface


class ITunableLoop(Interface):
    """Interface for self-tuning loop bodies to be driven by LoopTuner.

    To construct a self-tuning batched loop, define your loop body as a class
    implementing TunableLoop, and pass an instance to your LoopTuner.
    """
    def isDone():
        """Is this loop finished?

        Once this returns True, the LoopTuner will no longer touch this
        object.
        """

    def __call__(chunk_size):
        """Perform an iteration of the loop.

        The chunk_size parameter says (in some way you define) how much work
        the LoopTuner believes you should try to do in this iteration in order
        to get as close as possible to your time goal.
        """

    def cleanUp(self):
        """Clean up any open resources.

        Optional.

        This method is needed because loops may be aborted before
        completion, so clean up code in the isDone() method may
        never be invoked.
        """
