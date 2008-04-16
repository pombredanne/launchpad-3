# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Launchpad code-hosting system.

NOTE: Importing this package will load any system Bazaar plugins, as well as
all plugins in the bzrplugins/ directory underneath the rocketfuel checkout.
"""

__metaclass__ = type
__all__ = [
    'branch_id_to_path',
    'get_bzr_path',
    'get_bzr_plugins_path',
    'get_rocketfuel_root',
    'ProgressUIFactory',
    ]


import os.path
from bzrlib.plugin import load_plugins
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


def get_rocketfuel_root():
    """Find the root directory for this rocketfuel instance"""
    import bzrlib
    return os.path.dirname(os.path.dirname(os.path.dirname(bzrlib.__file__)))


def get_bzr_path():
    """Find the path to the copy of Bazaar for this rocketfuel instance"""
    return get_rocketfuel_root() + '/sourcecode/bzr/bzr'


def get_bzr_plugins_path():
    """Find the path to the Bazaar plugins for this rocketfuel instance"""
    return get_rocketfuel_root() + '/bzrplugins'


os.environ['BZR_PLUGIN_PATH'] = get_bzr_plugins_path()

# We want to have full access to Launchpad's Bazaar plugins throughout the
# codehosting package.
load_plugins()
