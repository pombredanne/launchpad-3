# Copyright 2004 Canonical Ltd.  All rights reserved.
#
"""ZODB integration for Launchpad.

To use:

>>> from canonical.zodb import zodbconnection
>>> resets = zodbconnection.passwordresets

"""
__metaclass__ = type

import zope.thread
from persistent.dict import PersistentDict
from zope.security.checker import ProxyFactory
from BTrees.OOBTree import OOBTree
from transaction import get_transaction

class ZODBConnection(zope.thread.local):
    """Thread local that stores the top-level ZODB object we care about."""
    passwordresets = None
    sessiondata = None

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
    if app.get('sessiondata') is None:
        app['sessiondata'] = OOBTree()

def bootstrapSubscriber(event):
    """Subscriber to the IDataBaseOpenedEvent.

    Creates zodb stuff if not already created.
    """
    db = event.database
    connection = db.open()
    root = connection.root()
    set_up_zodb_if_needed(root)
    get_transaction().commit()
    connection.close()

def handle_before_traversal(root):
    app = root[root_name]
    # Put the stuff we want access to in the thread local.
    zodbconnection.passwordresets = ProxyFactory(app['passwordresets'])
    zodbconnection.sessiondata = app['sessiondata']

