# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Optimized bulk operations against the database."""

__metaclass__ = type
__all__ = [
    'insert_many',
    'load',
    'load_referencing',
    'load_related',
    'reload',
    ]


from collections import defaultdict
from functools import partial
from operator import attrgetter

from storm.database import convert_param_marks
from storm.exceptions import (
    ClosedError,
    ConnectionBlockedError,
    )
from storm.expr import Or
from storm.info import get_cls_info
from storm.store import Store
from storm.tracer import trace
from zope.security.proxy import removeSecurityProxy

from lp.services.database.lpstorm import IStore


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


def _primary_key(object_type):
    """Get a primary key our helpers can use.

    :raises AssertionError if the key is missing or unusable.
    """
    primary_key = get_cls_info(object_type).primary_key
    if len(primary_key) != 1:
        raise AssertionError(
            "Compound primary keys are not supported: %s." %
            object_type.__name__)
    return primary_key[0]


def load(object_type, primary_keys, store=None):
    """Load a large number of objects efficiently."""
    primary_key = _primary_key(object_type)
    primary_key_column = primary_key
    primary_keys = set(primary_keys)
    primary_keys.discard(None)
    if not primary_keys:
        return []
    condition = primary_key_column.is_in(primary_keys)
    if store is None:
        store = IStore(object_type)
    return list(store.find(object_type, condition))


def load_referencing(object_type, owning_objects, reference_keys):
    """Load objects of object_type that reference owning_objects.

    Note that complex types like Person are best loaded through dedicated
    helpers that can eager load other related things (e.g. validity for
    Person).

    :param object_type: The object type to load - e.g. BranchSubscription.
    :param owning_objects: The objects which are referenced. E.g. [Branch()]
        At this point, all the objects should be of the same type, but that
        constraint could be lifted in future.
    :param reference_keys: A list of attributes that should be used to select
        object_type keys. e.g. ['branchID']
    :return: A list of object_type where any of reference_keys refered to the
        primary key of any of owning_objects.
    """
    store = IStore(object_type)
    if type(owning_objects) not in (list, tuple):
        owning_objects = tuple(owning_objects)
    if not owning_objects:
        return []
    exemplar = owning_objects[0]
    primary_key = _primary_key(get_type(exemplar))
    attribute = primary_key.name
    ids = set(map(attrgetter(attribute), owning_objects))
    conditions = []
    # Note to future self doing perf tuning: may want to make ids a WITH
    # clause.
    for column in map(partial(getattr, object_type), reference_keys):
        conditions.append(column.is_in(ids))
    return list(store.find(object_type, Or(conditions)))


def load_related(object_type, owning_objects, foreign_keys):
    """Load objects of object_type referred to by owning_objects.

    Note that complex types like Person are best loaded through dedicated
    helpers that can eager load other related things (e.g. validity for
    Person).

    :param object_type: The object type to load - e.g. Person.
    :param owning_objects: The objects holding the references. E.g. Bug.
    :param foreign_keys: A list of attributes that should be inspected for
        keys. e.g. ['ownerID']
    """
    keys = set()
    for owning_object in owning_objects:
        keys.update(map(partial(getattr, owning_object), foreign_keys))
    return load(object_type, keys)


def execute_many(store, statement, rows):
    """Invoke cursor.executemany for a Store.

    Adapted from Store.execute and Connection.execute.
    """
    if store._implicit_flush_block_count == 0:
        store.flush()
    connection = store._connection
    if connection._closed:
        raise ClosedError("Connection is closed")
    if connection._blocked:
        raise ConnectionBlockedError("Access to connection is blocked")
    if connection._event:
        connection._event.emit("register-transaction")
    connection._ensure_connected()
    statement = convert_param_marks(statement, "?", connection.param_mark)
    raw_cursor = connection._check_disconnect(connection.build_raw_cursor)
    connection._check_disconnect(
        trace, "execute_many", connection, raw_cursor,
        statement, rows or ())
    try:
        connection._check_disconnect(raw_cursor.executemany, statement, rows)
    except Exception, error:
        connection._check_disconnect(
            trace, "execute_many_success", connection, raw_cursor,
            statement, rows, error)
        raise
    else:
        connection._check_disconnect(
            trace, "connection_raw_execute_success", connection, raw_cursor,
            statement, rows)
    return raw_cursor


def insert_many(store, table, columns, rows):
    """Insert multiple rows into a table.

    :param store: Store to use for insertion.
    :param table: Name of the table to insert into.
    :param columns: Iterable of names of columns.
    :param rows: Sequence of tuples of values, in order as per columns.
    """
    def listify(values):
        return '(%s)' % ', '.join(values)
    column_str = listify(columns)
    values = listify(['?'] * len(columns))
    values = '(%s)' % ', '.join(['?' for column in columns])
    statement = "INSERT INTO %s %s VALUES %s" % (table, column_str, values)
    return execute_many(store, statement, rows)
