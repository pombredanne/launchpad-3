# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import copy
import operator
import sys
import warnings

from zope.interface import implements
from zope.interface.advice import addClassAdvisor
from zope.schema.interfaces import ITokenizedTerm, IVocabularyTokenized
from zope.security.proxy import isinstance as zope_isinstance

__all__ = [
    'Item',
    'DBItem',
    'DBSchema',
    'DBSchemaItem',
    'DBEnumeratedType',
    'EnumeratedType'
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


class DBSchemaItem:
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


class MetaEnum(type):

    implements(IVocabularyTokenized)

    def __new__(cls, classname, bases, classdict):

        # enforce items of dbenums have values
        # and items of others don't

        # if a sort_order is defined, make sure that it covers
        # all the items

        # only allow one base class
        if len(bases) > 1:
            raise TypeError(
                'Multiple inheritance is not allowed with '
                'EnumeratedType, %s.%s' % (
                classdict['__module__'], classname))

        if bases:
            base_class = bases[0]
            if hasattr(base_class, 'items'):
                for item in base_class.items:
                    if item.token not in classdict:
                        new_item = copy.copy(item)
                        classdict[item.token] = new_item

        # grab all the items:
        items = [(key, value) for key, value in classdict.iteritems()
                 if isinstance(value, Item)]
        if items:
            if bases and issubclass(bases[0], DBEnumeratedType):
                for id, item in items:
                    if not isinstance(value, DBItem):
                        raise TypeError(
                            'DBEnumeratedType items must be of type DBItem, '
                            '%s.%s.%s' % (
                            classdict['__module__'], classname, id))
            else:
                for id, item in items:
                    if isinstance(value, DBItem):
                        raise TypeError(
                            'EnumeratedType items must be of type Item, '
                            '%s.%s.%s' % (classdict['__module__'], classname, id))

        # Enforce capitalisation of items.
        for key, value in items:
            if key.upper() != key:
                raise TypeError(
                    'Item instance variable names must be capitalised.'
                    '  %s.%s.%s' % (classdict['__module__'], classname, key))

        # Override sort order if defined.
        if 'sort_order' in classdict:
            sort_order = classdict['sort_order']
            item_names = sorted([key for key, value in items])
            if item_names != sorted(sort_order):
                raise TypeError(
                    'sort_order for EnumeratedType must contain all and '
                    'only Item instances  %s.%s' % (
                    classdict['__module__'], classname))
            sort_id = 0
            for item_name in sort_order:
                classdict[item_name].sort_order = sort_id
                sort_id += 1

        # Set the id and schema for the type.
        item_lookup = {}
        for name, item in items:
            item.token = name
            item.schema = classname
            if item_lookup.get(item.value) is not None:
                raise TypeError(
                    'Item value "%s" is already defined in type %s.%s' %
                    (classdict['__module__'], classname))
            else:
                item_lookup[item.value] = item
        classdict['_item_lookup'] = item_lookup
        classdict['items'] = sorted([item for name, item in items],
                                    key=operator.attrgetter('sort_order'))
        classdict['name'] = classname
        classdict['description'] = classdict.get('__doc__', None)

        # If sort_order wasn't defined, define it based on the ordering.
        if 'sort_order' not in classdict:
            classdict['sort_order'] = tuple(
                [item.token for item in classdict['items']])

        return type.__new__(cls, classname, bases, classdict)

    def __contains__(self, value):
        """Return whether the value is available in this source
        """
        return value in self._item_lookup

    def __iter__(self):
        """Return an iterator which provides the terms from the vocabulary."""
        return self.items.__iter__()

    def __len__(self):
        """Return the number of valid terms, or sys.maxint."""
        return len(self.items)

    def getTerm(self, value):
        """Return the ITerm object for the term 'value'.

        If 'value' is not a valid term, this method raises LookupError.
        """
        result = self._item_lookup.get(value)
        if result is None:
            raise LookupError(value)
        return result

    def getTermByToken(self, token):
        """Return an ITokenizedTerm for the passed-in token.

        If `token` is not represented in the vocabulary, `LookupError`
        is raised. 
        """
        # The sort_order of the enumerated type lists all the items.
        if token not in self.sort_order:
            raise LookupError(token)
        # The token is the name of the attribute, so getattr suffices.
        return getattr(self, token)


class Item:
    """Items are the primary elements of the enumerated types.


    The schema attibute is a reference to the enumerated type that the
    Item is a member of.

    The token attribute is the name assigned to the Item.

    The value is the short text string used to identify the Item.
    """

    implements(ITokenizedTerm)

    schema = None
    sort_order = 0
    token = None
    value = None
    description = None
    
    def __init__(self, value, description=None):
        """Items are the main elements of the EnumeratedType.

        Where the value is passed in without a description,
        and the value looks like a docstring (has embedded carriage returns),
        the value is the first line, and the description is the rest.
        """

        self.sort_order = Item.sort_order
        Item.sort_order += 1

        self.value = value
        self.description = description

        if self.description is None:
            # check value
            if self.value.find('\n') != -1:
                self.value, self.description = docstring_to_title_descr(
                    self.value)

    def __int__(self):
        raise TypeError("Cannot cast Item to int.")

    def __eq__(self, other, stacklevel=2):
        if isinstance(other, int):
            warnings.warn('comparison of Item to an int: %r' % self,
                stacklevel=stacklevel)
            return False
        elif zope_isinstance(other, Item):
            return self.token == other.token and self.schema == other.schema
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other, stacklevel=3)

    def __lt__(self, other):
        return self.sort_order < other.sort_order

    def __gt__(self, other):
        return self.sort_order > other.sort_order

    def __le__(self, other):
        return self.sort_order <= other.sort_order

    def __ge__(self, other):
        return self.sort_order >= other.sort_order

    def __hash__(self):
        return hash(self.value)

    def __str__(self):
        return str(self.value)
    
    def __repr__(self):
        return "<Item %s.%s, %s>" % (
            self.schema, self.token, self.value)


class DBItem(Item):
    """The DBItem refers to an enumerated item that is used in the database.

    Database enumerations are stored in the database using integer columns.
    """

    def __init__(self, db_value, value, description=None):
        Item.__init__(self, value, description)
        self.db_value = db_value

    def __hash__(self):
        return self.db_value

    def __str__(self):
        return self.db_value
    
    def __repr__(self):
        return "<DBItem %s.%s, (%d) %s>" % (
            self.schema, self.token, self.db_value, self.value)

    def __sqlrepr__(self, dbname):
        return repr(self.db_value)
            

class EnumeratedType:
    __metaclass__ = MetaEnum

    items = ()


class DBEnumeratedType(EnumeratedType):
    pass


def extends(*enum_types):
    frame = sys._getframe(1)
    locals = frame.f_locals
    
    # import pdb; pdb.set_trace()

    # Try to make sure we were called from a class def
    if (locals is frame.f_globals) or ('__module__' not in locals):
        raise TypeError("Item can be used only from a class definition.")

    frame.f_locals['omigod'] = 'Fubar'

    return 'Fubar'
