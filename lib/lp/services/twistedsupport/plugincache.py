# Copyright 2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Build dropin.cache for all installed Twisted plugins.

This would be built on the fly if we didn't do it here, but we want to make
sure to build it in a predictable environment.  In particular, if a plugin's
cache is first built as a result of being run via ampoule, then ampoule will
fail if any part of the process of importing the plugin installs a default
reactor.
"""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type

from twisted.plugin import (
    getPlugins,
    IPlugin,
    )


def main():
    list(getPlugins(IPlugin))
