# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Optimized bulk operations against the database."""

__metaclass__ = type
__all__ = [
    'reload',
    ]


from collections import defaultdict

from storm.info import get_cls_info
from storm.store import Store
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces.lpstorm import IStore


def collate(things, key):
    """Collate the given objects according to a key function.

    Generates (common-key-value, list-of-things) tuples, like groupby,
    except that the given objects do not need to be sorted.
    """
    collection = defaultdict(list)
    for thing in things:
        collection[key(thing)].append(thing)
    return collection.iteritems()


def get_type(thing):
    """Return the type of the given object.

    If the given object is wrapped by a security proxy, the type
    returned is that of the wrapped object.
    """
    return type(removeSecurityProxy(thing))


def gen_reload_queries(objects):
    """Prepare queries to reload the given objects."""
    for object_type, objects in collate(objects, get_type):
        primary_key = get_cls_info(object_type).primary_key
        if len(primary_key) != 1:
            raise AssertionError(
                "Compound primary keys are not supported: %s." %
                object_type.__name__)
        primary_key_column = primary_key[0]
        primary_key_column_getter = primary_key_column.__get__
        for store, objects in collate(objects, Store.of):
            primary_keys = map(primary_key_column_getter, objects)
            condition = primary_key_column.is_in(primary_keys)
            yield store.find(object_type, condition)


def reload(objects):
    """Reload a large number of objects efficiently."""
    for query in gen_reload_queries(objects):
        list(query)


def load(object_type, primary_keys, store=None):
    """Load a large number of objects efficiently."""
    primary_key = get_cls_info(object_type).primary_key
    if len(primary_key) != 1:
        raise AssertionError(
            "Compound primary keys are not supported: %s." %
            object_type.__name__)
    primary_key_column = primary_key[0]
    condition = primary_key_column.is_in(set(primary_keys))
    if store is None:
        store = IStore(object_type)
    query = store.find(object_type, condition)
    return list(query)
