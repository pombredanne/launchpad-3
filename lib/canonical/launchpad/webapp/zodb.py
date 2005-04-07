# Copyright 2004 Canonical Ltd.  All rights reserved.
#
"""ZODB integration for Launchpad.

To use:

>>> from canonical.launchpad.webapp.zodb import zodbconnection
>>> resets = zodbconnection.annotations

"""
__metaclass__ = type

import zope.thread
from persistent.dict import PersistentDict
from zope.security.checker import ProxyFactory
from BTrees.OOBTree import OOBTree
from transaction import get_transaction

class ZODBConnection(zope.thread.local):
    """Thread local that stores the top-level ZODB object we care about."""
    sessiondata = None
    annotations = None

zodbconnection = ZODBConnection()

root_name = "Launchpad"

def set_up_zodb_if_needed(root):
    app = root.get(root_name, None)
    if app is None:
        root[root_name] = PersistentDict()
        app = root[root_name]
    if app.get('sessiondata') is None:
        app['sessiondata'] = OOBTree()
    if app.get('annotations') is None:
        app['annotations'] = OOBTree()

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
    zodbconnection.sessiondata = app['sessiondata']
    zodbconnection.annotations = app['annotations']

