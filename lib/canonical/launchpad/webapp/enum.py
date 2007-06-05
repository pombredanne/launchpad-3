# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import sys
import warnings

from zope.interface.advice import addClassAdvisor
from zope.security.proxy import isinstance as zope_isinstance

__all__ = [
    'Item',
    'DBSchema'
    ]

def docstring_to_title_descr(string):
    """When given a classically formatted docstring, returns a tuple
    (title,x description).

    >>> class Foo:
    ...     '''
    ...     Title of foo
    ...
    ...     Description of foo starts here.  It may
    ...     spill onto multiple lines.  It may also have
    ...     indented examples:
    ...
    ...       Foo
    ...       Bar
    ...
    ...     like the above.
    ...     '''
    ...
    >>> title, descr = docstring_to_title_descr(Foo.__doc__)
    >>> print title
    Title of foo
    >>> for num, line in enumerate(descr.splitlines()):
    ...    print "%d.%s" % (num, line)
    ...
    0.Description of foo starts here.  It may
    1.spill onto multiple lines.  It may also have
    2.indented examples:
    3.
    4.  Foo
    5.  Bar
    6.
    7.like the above.

    """
    lines = string.splitlines()
    # title is the first non-blank line
    for num, line in enumerate(lines):
        line = line.strip()
        if line:
            title = line
            break
    else:
        raise ValueError
    assert not lines[num+1].strip()
    descrlines = lines[num+2:]
    descr1 = descrlines[0]
    indent = len(descr1) - len(descr1.lstrip())
    descr = '\n'.join([line[indent:] for line in descrlines])
    return title, descr


class OrderedMapping:

    def __init__(self, mapping):
        self.mapping = mapping

    def __getitem__(self, key):
        if key in self.mapping:
            return self.mapping[key]
        else:
            for k, v in self.mapping.iteritems():
                if v.name == key:
                    return v
            raise KeyError, key

    def __iter__(self):
        L = self.mapping.items()
        L.sort()
        for k, v in L:
            yield v


class ItemsDescriptor:

    def __get__(self, inst, cls=None):
        return OrderedMapping(cls._items)


class Item:
    """An item in an enumerated type.

    An item has a name, title and description.  It also has an integer value.

    An item has a sortkey, which defaults to its integer value, but can be
    set specially in the constructor.

    """

    def __init__(self, value, title, description=None, sortkey=None):
        frame = sys._getframe(1)
        locals = frame.f_locals

        # Try to make sure we were called from a class def
        if (locals is frame.f_globals) or ('__module__' not in locals):
            raise TypeError("Item can be used only from a class definition.")

        addClassAdvisor(self._setClassFromAdvice)
        try:
            self.value = int(value)
        except ValueError:
            raise TypeError("value must be an int, not %r" % (value,))
        if description is None:
            self.title, self.description = docstring_to_title_descr(title)
        else:
            self.title = title
            self.description = description
        if sortkey is None:
            self.sortkey = self.value
        else:
            self.sortkey = sortkey

    def _setClassFromAdvice(self, cls):
        self.schema = cls
        names = [k for k, v in cls.__dict__.iteritems() if v is self]
        assert len(names) == 1
        self.name = names[0]
        if not hasattr(cls, '_items'):
            cls._items = {}
        cls._items[self.value] = self
        return cls

    def __int__(self):
        raise TypeError("Cannot cast Item to int.  Use item.value instead.")

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return "<Item %s (%d) from %s>" % (self.name, self.value, self.schema)

    def __sqlrepr__(self, dbname):
        return repr(self.value)

    def __eq__(self, other, stacklevel=2):
        if isinstance(other, int):
            warnings.warn('comparison of DBSchema Item to an int: %r' % self,
                stacklevel=stacklevel)
            return False
        elif zope_isinstance(other, Item):
            return self.value == other.value and self.schema == other.schema
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other, stacklevel=3)

    def __lt__(self, other):
        return self.sortkey < other.sortkey

    def __gt__(self, other):
        return self.sortkey > other.sortkey

    def __le__(self, other):
        return self.sortkey <= other.sortkey

    def __ge__(self, other):
        return self.sortkey >= other.sortkey

    def __hash__(self):
        return self.value

    # These properties are provided as a way to get at the other
    # schema items and name from a security wrapped Item instance when
    # there are no security declarations for the DBSchema class.  They
    # are used by the enumvalue TALES expression.
    @property
    def schema_items(self):
        return self.schema.items

    @property
    def schema_name(self):
        return self.schema.__name__

# TODO: make a metaclass for dbschemas that looks for ALLCAPS attributes
#       and makes the introspectible.
#       Also, makes the description the same as the docstring.
#       Also, sets the name on each Item based on its name.
#       (Done by crufty class advice at present.)
#       Also, set the name on the DBSchema according to the class name.
#
#       Also, make item take just one string, optionally, and parse that
#       to make something appropriate.

class DBSchema:
    """Base class for database schemas."""

    # TODO: Make description a descriptor that automatically refers to the
    #       docstring.
    description = "See body of class's __doc__ docstring."
    title = "See first line of class's __doc__ docstring."
    name = "See lower-cased-spaces-inserted class name."
    items = ItemsDescriptor()

