# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import copy
import itertools
import operator
import sys
import warnings

from zope.interface import implements
from zope.interface.advice import addClassAdvisor
from zope.schema.interfaces import ITitledTokenizedTerm, IVocabularyTokenized
from zope.security.proxy import isinstance as zope_isinstance

__all__ = [
    'Item',
    'DBItem',
    'TokenizedItem',
    'DBSchema',
    'DBSchemaItem',
    'DBEnumeratedType',
    'EnumeratedType',
    'use_template',
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
        elif zope_isinstance(other, DBSchemaItem):
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


class Item:
    """Items are the primary elements of the enumerated types.

    The enum attibute is a reference to the enumerated type that the
    Item is a member of.

    The token attribute is the name assigned to the Item.

    The value is the short text string used to identify the Item.
    """

    sort_order = 0
    name = None
    description = None
    title = None

    def __init__(self, title, description=None):
        """Items are the main elements of the EnumeratedType.

        Where the value is passed in without a description,
        and the value looks like a docstring (has embedded carriage returns),
        the value is the first line, and the description is the rest.
        """

        self.sort_order = Item.sort_order
        Item.sort_order += 1
        self.title = title

        self.description = description

        if self.description is None:
            # check value
            if self.title.find('\n') != -1:
                self.title, self.description = docstring_to_title_descr(
                    self.title)

    def __int__(self):
        raise TypeError("Cannot cast Item to int.")

    def __cmp__(self, other):
        if zope_isinstance(other, Item):
            return cmp(self.sort_order, other.sort_order)
        else:
            raise TypeError(
                'Comparisons of Items are only valid with other Items')

    def __eq__(self, other, stacklevel=2):
        if isinstance(other, int):
            warnings.warn('comparison of Item to an int: %r' % self,
                stacklevel=stacklevel)
            return False
        elif zope_isinstance(other, Item):
            return (self.name == other.name and
                    self.enum == other.enum)
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other, stacklevel=3)

    def __hash__(self):
        return hash(self.title)

    def __str__(self):
        return str(self.title)

    def __repr__(self):
        return "<Item %s.%s, %s>" % (
            self.enum.name, self.name, self.title)


class DBItem(Item):
    """The DBItem refers to an enumerated item that is used in the database.

    Database enumerations are stored in the database using integer columns.
    """

    def __init__(self, value, title, description=None):
        Item.__init__(self, title, description)
        self.value = value

    def __hash__(self):
        return self.value

    def __repr__(self):
        return "<DBItem %s.%s, (%d) %s>" % (
            self.enum.name, self.name, self.value, self.title)

    def __sqlrepr__(self, dbname):
        return repr(self.value)


class TokenizedItem:
    """Wraps an `Item` or `DBItem` to provide `ITitledTokenizedTerm`."""

    implements(ITitledTokenizedTerm)

    def __init__(self, item):
        self.value = item
        self.token = item.name
        self.title = item.title


class MetaEnum(type):

    implements(IVocabularyTokenized)

    item_type = Item
    enum_name = 'EnumeratedType'

    def __new__(cls, classname, bases, classdict):

        # enforce items of dbenums have values
        # and items of others don't

        # if a sort_order is defined, make sure that it covers
        # all the items

        # only allow one base class
        if len(bases) > 1:
            raise TypeError(
                'Multiple inheritance is not allowed with '
                '%s, %s.%s' % (
                cls.enum_name, classdict['__module__'], classname))

        if bases:
            base_class = bases[0]
            if hasattr(base_class, 'items'):
                for item in base_class.items:
                    if item.name not in classdict:
                        new_item = copy.copy(item)
                        classdict[item.name] = new_item

        # grab all the items:
        items = [(key, value) for key, value in classdict.iteritems()
                 if isinstance(value, Item)]
        # Enforce that all the items are of the appropriate type.
        for key, value in items:
            if not isinstance(value, cls.item_type):
                raise TypeError(
                    'Items must be of the appropriate type for the '
                    '%s, %s.%s.%s' % (
                    cls.enum_name, classdict['__module__'], classname, key))

        # Enforce capitalisation of items.
        for key, value in items:
            if key.upper() != key:
                raise TypeError(
                    'Item instance variable names must be capitalised.'
                    '  %s.%s.%s' % (classdict['__module__'], classname, key))

        # Override item's default sort order if sort_order is defined.
        if 'sort_order' in classdict:
            sort_order = classdict['sort_order']
            item_names = sorted([key for key, value in items])
            if item_names != sorted(sort_order):
                raise TypeError(
                    'sort_order for %s must contain all and '
                    'only Item instances  %s.%s' % (
                    cls.enum_name, classdict['__module__'], classname))
            sort_id = 0
            for item_name in sort_order:
                classdict[item_name].sort_order = sort_id
                sort_id += 1

        for name, item in items:
            item.name = name

        classdict['items'] = sorted([item for name, item in items],
                                    key=operator.attrgetter('sort_order'))
        classdict['name'] = classname
        classdict['description'] = classdict.get('__doc__', None)

        # If sort_order wasn't defined, define it based on the ordering.
        if 'sort_order' not in classdict:
            classdict['sort_order'] = tuple(
                [item.name for item in classdict['items']])

        instance = type.__new__(cls, classname, bases, classdict)

        # Add a reference to the enumerated type to each item.
        for item in instance.items:
            item.enum = instance

        return instance

    def __contains__(self, value):
        """See `ISource`."""
        return value in self.items

    def __iter__(self):
        """See `IIterableVocabulary`."""
        return itertools.imap(TokenizedItem, self.items)

    def __len__(self):
        """See `IIterableVocabulary`."""
        return len(self.items)

    def getTerm(self, value):
        """See `IBaseVocabulary`."""
        if value in self.items:
            return TokenizedItem(value)
        raise LookupError(value)

    def getTermByToken(self, token):
        """See `IVocabularyTokenized`."""
        # The sort_order of the enumerated type lists all the items.
        if token in self.sort_order:
            return TokenizedItem(getattr(self, token))
        else:
            # If the token is not specified in the sort order then check
            # the titles of the items.  This is to support the transition
            # of accessing items by their titles.  To continue support
            # of old URLs et al, this will probably stay for some time.
            for item in self.items:
                if item.title == token:
                    return TokenizedItem(item)
        # The token was not in the sort_order (and hence the name of a
        # variable), nor was the token the title of one of the items.
        raise LookupError(token)

    def __repr__(self):
        return "<EnumeratedType '%s'>" % self.name


class MetaDBEnum(MetaEnum):

    item_type = DBItem
    enum_name = 'DBEnumeratedType'

    def getDBItemByValue(self, value):
        """Return the `DBItem` object for the database 'value'."""
        try:
            return dict((item.value, item) for item in self.items)[value]
        except KeyError:
            raise LookupError(value)


class EnumeratedType:
    __metaclass__ = MetaEnum
    # items = ()


class DBEnumeratedType:
    __metaclass__ = MetaDBEnum
    # items = ()

def use_template(enum_type, include=None, exclude=None):
    """An alternative way to extend an enumerated type as opposed to inheritance.

    The parameters include and exclude shoud either be the name values of the
    items (the parameter names), or a list or tuple that contains string values.
    """
    frame = sys._getframe(1)
    locals = frame.f_locals

    # Try to make sure we were called from a class def.
    if (locals is frame.f_globals) or ('__module__' not in locals):
        raise TypeError(
            "use_template can be used only from a class definition.")

    # You can specify either includes or excludes, not both.
    if include and exclude:
        raise ValueError("You can specify includes or excludes not both.")

    if include is None:
        items = enum_type.items
    else:
        if isinstance(include, str):
            include = [include]
        items = [item for item in enum_type.items if item.name in include]

    if exclude is None:
        exclude = []
    elif isinstance(exclude, str):
        exclude = [exclude]

    for item in items:
        if item.name not in exclude:
            locals[item.name] = copy.copy(item)
