# Copyright 2004 Canonical Ltd.  All rights reserved.
"""System for annotating objects and storing annotations in the zodb."""

__metaclass__ = type

from zope.interface import Interface, implements
from zope.proxy import removeAllProxies
from BTrees.OOBTree import OOBTree
from persistent.dict import PersistentDict
from canonical.launchpad.webapp.zodb import zodbconnection
from canonical.launchpad.interfaces import IZODBAnnotation

class SQLObjectAnnotation:
    implements(IZODBAnnotation)

    def __init__(self, sqlobject):
        # TODO: make this write lazily on a new PersistentDict only if
        #       it is actually written to

        # Use the str of the id so that if we have str objectids in
        # the future, the BTrees won't go insane.
        objectid = str(sqlobject.id)

        all_annotations = zodbconnection.annotations
        classname = sqlobject.__class__.__name__
        if classname not in all_annotations:
            all_annotations[classname] = OOBTree()

        annotations_for_class = all_annotations[classname]
        if objectid not in annotations_for_class:
            annotations_for_class[objectid] = PersistentDict()

        annotations = annotations_for_class[objectid]
        self.annotations = annotations

    def __getitem__(self, namespace):
        marker = object()
        value = self.get(namespace, marker)
        if value is marker:
            raise KeyError, namespace
        else:
            return value

    def get(self, namespace, default=None):
        return self.annotations.get(namespace, default)

    def __setitem__(self, namespace, value):
        self.annotations[namespace] = removeAllProxies(value)

    def __contains__(self, namespace):
        return namespace in self.annotations

    def __delitem__(self, namespace):
        del self.annotations[namespace]
