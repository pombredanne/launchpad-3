# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""A generic collection of database objects."""

__metaclass__ = type
__all__ = [
    'Collection',
    ]


class Collection(object):
    """An arbitrary collection of database objects."""

    def __init__(self, base=None, conditions=None):
        """Construct a collection, possibly based on another one."""
        if base is None:
            self.conditions = []
        else:
            self.conditions = base.conditions
        if conditions is not None:
            self.conditions += conditions

    def select(self, values, store=None):
        """Return the selected values from the collection."""
