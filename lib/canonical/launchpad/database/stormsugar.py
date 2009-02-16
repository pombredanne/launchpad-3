# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Storm is powerful stuff.  This helps it go down more easily."""

__metaclass__ = type

from storm.locals import Int, Store, Storm
from zope.component import getUtility

from canonical.launchpad.webapp.interfaces import (
     DEFAULT_FLAVOR, IStoreSelector, MAIN_STORE, MASTER_FLAVOR)


class ObjectNotFound(Exception):
    """Exception raised when a storm object can't be got."""

    def __init__(self, orm_class, id):
        msg = 'Not found: %s with id %s.' % (orm_class.__name__, id)
        Exception.__init__(self, msg)


class UnknownProperty(Exception):
    """The property name specified in a kwarg is not pre-defined."""
    def __init__(self, orm_class, name):
        msg = 'Class %s has no property "%s".' % (orm_class.__name__, name)
        Exception.__init__(self, msg)


class Sugar:
    """Base class providing convenient Storm API."""

    __store_type__ = MAIN_STORE

    id = Int(primary=True)

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if getattr(self.__class__, key, None) is None:
                raise UnknownProperty(self.__class__, key)
            setattr(self, key, value)
        self.master_store.add(self)

    @property
    def master_store(self):
        selector = getUtility(IStoreSelector)
        return selector.get(self.__store_type__, MASTER_FLAVOR)

    @classmethod
    def getDefaultStore(klass):
        """Return the default store for this class."""
        selector = getUtility(IStoreSelector)
        return selector.get(klass.__store_type__, DEFAULT_FLAVOR)

    @classmethod
    def get(klass, id):
        """Return the object of this type with given id."""
        store = klass.getDefaultStore()
        obj = store.get(klass, id)
        if obj is None:
            raise ObjectNotFound(klass, id)
        return obj

    def destroySelf(self):
        """Remote this object from the database."""
        Store.of(self).remove(self)
