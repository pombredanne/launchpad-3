# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Launchpad code-hosting system.

NOTE: Importing this package will load any system Bazaar plugins, as well as
all plugins in the bzrplugins/ directory underneath the rocketfuel checkout.
"""

__metaclass__ = type
__all__ = [
    'get_bzr_path',
    'get_bzr_plugins_path',
    'get_rocketfuel_root',
    ]


import os.path
from bzrlib.plugin import load_plugins


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
load_plugins([get_bzr_plugins_path()])
