# Copyright 2004 Canonical Ltd.  All rights reserved.
#
# arch-tag: 490df5ca-e28a-4e73-8c3b-8a00fd195f45
"""ZODB integration for Launchpad.

To use:

>>> from canonical.zodb import zodbconnection
>>> resets = zodbconnection.passwordresets

"""
__metaclass__ = type

import zope.thread
from persistent.dict import PersistentDict
from zope.security.checker import ProxyFactory


class ZODBConnection(zope.thread.local):
    """Thread local that stores the top-level ZODB object we care about."""
    passwordresets = None

zodbconnection = ZODBConnection()

root_name = "Launchpad"

def set_up_zodb_if_needed(root):
    app = root.get(root_name, None)
    if app is None:
        root[root_name] = PersistentDict()
        app = root[root_name]
    if app.get('passwordresets') is None:
        # import is here because the set-up of PasswordResets should be
        # moved into canonical.auth, by means of a start-up event.
        # (Ideally, a special start-up event that doesn't occur on all
        #  zeo clients.)
        from canonical.auth import PasswordResets
        app['passwordresets'] = PasswordResets()

def handle_before_traversal(root):
    # XXX Move the next two lines to a startup event handler
    set_up_zodb_if_needed(root)

    app = root[root_name]
    # Put the password resets into the thread local
    zodbconnection.passwordresets = ProxyFactory(app['passwordresets'])

