# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Optimized bulk operations against the database."""

__metaclass__ = type
__all__ = [
    'reload',
    ]


from collections import defaultdict

from zope.security.proxy import removeSecurityProxy

from storm.base import Storm
from storm.expr import In
from storm.info import get_cls_info
from storm.store import Store


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
        if not issubclass(object_type, Storm):
            raise AssertionError(
                "Cannot load objects of type %s: %r" % (
                    object_type.__name__, objects))
        primary_key = get_cls_info(object_type).primary_key
        if len(primary_key) != 1:
            raise AssertionError(
                "Compound primary keys are not supported: %s." %
                object_type.__name__)
        primary_key_column = primary_key[0]
        primary_key_column_getter = primary_key_column.__get__
        for store, objects in collate(objects, Store.of):
            primary_keys = map(primary_key_column_getter, objects)
            condition = In(primary_key_column, primary_keys)
            yield store.find(object_type, condition)


def reload(objects):
    """Reload a large number of objects efficiently."""
    for query in gen_reload_queries(objects):
        list(query)
