# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""A generic collection of database objects."""

__metaclass__ = type
__all__ = [
    'Collection',
    ]


class Collection(object):
    """An arbitrary collection of database objects."""

    store = None

    def __init__(self, base, *conditions):
        """Construct a collection, possibly based on another one."""
        if base is None:
            base_conditions = (True, )
        else:
            base_conditions = base.conditions
        self.conditions = base_conditions + conditions

    def use(self, store):
        """Return a copy of this collection that uses the given store."""

    def select(self, *values):
        """Return the selected values from the collection."""
