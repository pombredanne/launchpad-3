# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=C0203

"""Storm is powerful stuff.  This helps it go down more easily.

This module is experimental.  Please give feedback and feel free to adjust it.
"""

__metaclass__ = type


__all__ = [
    'ForeignKey',
    'ObjectNotFound',
    'Sugar',
    'UnknownProperty',
    ]


from storm.locals import (
    Int,
    Reference,
    Store,
    Storm,
    )
from zope.component import getUtility

from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    MASTER_FLAVOR,
    )
from lp.app.errors import NotFoundError


class ObjectNotFound(NotFoundError):
    """Exception raised when a storm object can't be got."""

    def __init__(self, orm_class, id):
        msg = 'Not found: %s with id %s.' % (orm_class.__name__, id)
        NotFoundError.__init__(self, msg)


class UnknownProperty(Exception):
    """The property name specified in a kwarg is not pre-defined."""

    def __init__(self, orm_class, name):
        msg = 'Class %s has no property "%s".' % (orm_class.__name__, name)
        Exception.__init__(self, msg)


class ForeignKey(Reference):

    def __init__(self, remote_key, name=None):
        self.name = name
        Reference.__init__(self, None, remote_key)


# Use Storm.__metaclass__ because storm.properties.PropertyPublisherMeta isn't
# in an __all__.

class Sugary(Storm.__metaclass__):
    """Metaclass that adds support for ForeignKey."""

    def __init__(cls, name, bases, dict):
        for key in dir(cls):
            val = getattr(cls, key, None)
            if not isinstance(val, ForeignKey):
                continue
            col_name = val.name
            if col_name is None:
                col_name = key
            val._local_key = Int(col_name)
            setattr(cls, '_%s_id' % key, val._local_key)
        # Do this last, because it wants References to have their local_key
        # properly set up.
        super(Sugary, cls).__init__(name, bases, dict)


class Sugar(Storm):
    """Base class providing convenient Storm API."""

    __metaclass__ = Sugary

    __store_type__ = MAIN_STORE

    id = Int(primary=True)

    def __init__(self, **kwargs):
        super(Sugar).__init__(Sugar, self)
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
    def getById(klass, id):
        """Return the object of this type with given id."""
        store = klass.getDefaultStore()
        obj = store.get(klass, id)
        if obj is None:
            raise ObjectNotFound(klass, id)
        return obj

    @classmethod
    def find(klass, **kwargs):
        """Select the instances whose properties match kwargs."""
        assert len(kwargs) > 0
        store = klass.getDefaultStore()
        return store.find(klass, **kwargs)

    def flush(self):
        """Bi-directionally update this object with the database."""
        store = Store.of(self)
        store.flush()
        store.autoreload(self)

    def remove(self):
        """Remove this object from the database."""
        Store.of(self).remove(self)
