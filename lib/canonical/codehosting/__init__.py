# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Launchpad code-hosting system."""

__metaclass__ = type
__all__ = ['branch_id_to_path', 'ProgressUIFactory']


from bzrlib.progress import ProgressBarStack
from bzrlib.ui import SilentUIFactory


class ProgressUIFactory(SilentUIFactory):
    """A UI Factory that installs a progress bar of your choice."""

    def __init__(self, progress_bar_factory):
        """Construct a ProgressUIFactory.

        :param progress_bar_factory: A callable that returns a
            ProgressBar.  It must take up to 8 arguments.
        """
        super(ProgressUIFactory, self).__init__()
        self._progress_bar_factory = progress_bar_factory

    def nested_progress_bar(self):
        """See `bzrlib.ui.UIFactory.nested_progress_bar`."""
        if self._progress_bar_stack is None:
            self._progress_bar_stack = ProgressBarStack(
                klass=self._progress_bar_factory)
        return self._progress_bar_stack.get_nested()


def branch_id_to_path(branch_id):
    """Convert the given branch ID into NN/NN/NN/NN form, where NN is a two
    digit hexadecimal number.

    Some filesystems are not capable of dealing with large numbers of inodes.
    The supermirror, which can potentially have tens of thousands of branches,
    needs the branches split into several directories. The launchpad id is
    used in order to determine the splitting.
    """
    h = "%08x" % int(branch_id)
    return '%s/%s/%s/%s' % (h[:2], h[2:4], h[4:6], h[6:])
