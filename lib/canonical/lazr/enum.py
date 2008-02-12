# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import itertools
import operator
import sys
import warnings

from zope.interface import Attribute, Interface, implements
from zope.schema.interfaces import ITitledTokenizedTerm, IVocabularyTokenized
from zope.security.proxy import isinstance as zope_isinstance
from canonical.lazr.interfaces import IJSONPublishable

__all__ = [
    'BaseItem',
    'DBEnumeratedType',
    'DBItem',
    'EnumeratedType',
    'IEnumeratedType',
    'Item',
    'TokenizedItem',
    'enumerated_type_registry',
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


class BaseItem:
    """Items are the primary elements of the enumerated types.

    `BaseItem` is the base class for both `Item` and `DBItem`.

    The enum attribute is a reference to the enumerated type that the
    Item is a member of.

    The token attribute is the name assigned to the item.

    The value is the short text string used to identify the item.
    """

    sortkey = 0
    name = None
    description = None
    title = None

    def __init__(self, title, description=None):
        """Items are the main elements of the EnumeratedType.

        Where the title is passed in without a description,
        and the title looks like a docstring (has embedded carriage returns),
        the title is the first line, and the description is the rest.
        """

        self.sortkey = BaseItem.sortkey
        BaseItem.sortkey += 1
        self.title = title
        # The enum attribute is set duing the class constructor of the
        # containing enumerated type.

        self.description = description

        if self.description is None:
            # check value
            if self.title.find('\n') != -1:
                self.title, self.description = docstring_to_title_descr(
                    self.title)

    def __int__(self):
        raise TypeError("Cannot cast Item to int.")

    def __cmp__(self, other):
        if zope_isinstance(other, BaseItem):
            return cmp(self.sortkey, other.sortkey)
        else:
            raise TypeError(
                'Comparisons of Items are only valid with other Items')

    def __eq__(self, other, stacklevel=2):
        if isinstance(other, int):
            warnings.warn('comparison of Item to an int: %r' % self,
                stacklevel=stacklevel)
            return False
        elif zope_isinstance(other, BaseItem):
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


class Item(BaseItem):
    """The `Item` is an element of an `EnumeratedType`."""
    @staticmethod
    def construct(other_item):
        """Create an Item based on the other_item."""
        item = Item(other_item.title, other_item.description)
        item.sortkey = other_item.sortkey
        return item

    def __repr__(self):
        return "<Item %s.%s, %s>" % (
            self.enum.name, self.name, self.title)


class DBItem(BaseItem):
    """The `DBItem` refers to an enumerated item that is used in the database.

    Database enumerations are stored in the database using integer columns.
    """

    @staticmethod
    def construct(other_item):
        """Create an Item based on the other_item."""
        item = DBItem(
            other_item.value, other_item.title, other_item.description)
        item.sortkey = other_item.sortkey
        return item

    def __init__(self, value, title, description=None):
        BaseItem.__init__(self, title, description)
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


# The enumerated_type_registry is a mapping of all enumerated types to the
# actual class.  There should only ever be one EnumeratedType or
# DBEnumerateType with a particular name.  This serves two purposes:
#   * a way to get any enumerated type by its name (used in tales.py)
#   * a way to iterate over the DBEnumeratedTypes in order to confirm the
#     values actually stored in the database.
enumerated_type_registry = {}


class EnumItems:
    """Allow access to Items of an enumerated type using names or db values.

    Access can be made to the items using the name of the Item.

    If the enumerated type has DBItems then the mapping includes a mapping of
    the database integer values to the DBItems.
    """
    def __init__(self, items, mapping):
        self.items = items
        self.mapping = mapping
    def __getitem__(self, key):
        if key in self.mapping:
            return self.mapping[key]
        else:
            raise KeyError(key)
    def __iter__(self):
        return self.items.__iter__()
    def __len__(self):
        return len(self.items)


class IEnumeratedType(Interface):
    """Defines the attributes that EnumeratedTypes have."""
    name = Attribute(
        "The name of the EnumeratedType is the same as the name of the class.")
    description = Attribute(
        "The description is the docstring of the EnumeratedType class.")
    sort_order = Attribute(
        "A tuple of Item names that is used to determine the ordering of the "
        "Items.")
    items = Attribute(
        "An instance of `EnumItems` which allows access to the enumerated "
        "types items by either name of database value if the items are "
        "DBItems.")


class BaseMetaEnum(type):
    """The metaclass functionality for `EnumeratedType` and `DBEnumeratedType`.

    This metaclass defines methods that allow the enumerated types to implement
    the IVocabularyTokenized interface.

    The metaclass also enforces "correct" definitions of enumerated types by
    enforcing capitalisation of Item variable names and defining an appropriate
    ordering.
    """
    implements(IEnumeratedType, IVocabularyTokenized)

    @classmethod
    def _enforceSingleInheritance(cls, classname, bases, classdict):
        """Only one base class is allowed for enumerated types."""
        if len(bases) > 1:
            raise TypeError(
                'Multiple inheritance is not allowed with '
                '%s, %s.%s' % (
                cls.enum_name, classdict['__module__'], classname))

    @classmethod
    def _updateClassDictWithBaseItems(cls, bases, classdict):
        """Copy each of the items from the base class that hasn't been
        explicitly defined in the new class."""
        if bases:
            base_class = bases[0]
            if hasattr(base_class, 'items'):
                for item in base_class.items:
                    if item.name not in classdict:
                        new_item = cls.item_type.construct(item)
                        classdict[item.name] = new_item

    @classmethod
    def _updateClassDictWithTemplateItems(cls, classdict):
        """If constructed through use_template, we need to construct
        the appropriate type of items based on our item_type of our class."""
        if 'template_items' in classdict:
            for item in classdict['template_items']:
                classdict[item.name] = cls.item_type.construct(item)
            # The template_items key is not wanted or needed in the new type.
            del classdict['template_items']

    @classmethod
    def _enforceItemClassAndName(cls, items, classname, module_name):
        """All items must be of the appropriate type for the enumeration type.

        All item variable names must be capitalised.
        """
        for item_name, item in items:
            if not isinstance(item, cls.item_type):
                raise TypeError(
                    'Items must be of the appropriate type for the '
                    '%s, %s.%s.%s' % (
                    cls.enum_name, module_name, classname, item_name))

            if item_name.upper() != item_name:
                raise TypeError(
                    'Item instance variable names must be capitalised.'
                    '  %s.%s.%s' % (module_name, classname, item_name))

            item.name = item_name

    @classmethod
    def _generateItemMapping(cls, items):
        """Each enumerated type has a mapping of the item names to the item
        instances."""
        return dict(items)

    @classmethod
    def _enforceSortOrder(cls, classname, classdict, items):
        """ Override item's default sort order if sort_order is defined.

        :return: A list of items ordered appropriately.
        """
        items = dict(items)
        if 'sort_order' in classdict:
            sort_order = classdict['sort_order']
            item_names = sorted(items.keys())
            if item_names != sorted(sort_order):
                raise TypeError(
                    'sort_order for %s must contain all and '
                    'only Item instances  %s.%s' % (
                    cls.enum_name, classdict['__module__'], classname))
        else:
            # Sort the items by the automatically generated
            # sortkey.
            sort_order = [
                item.name for item in sorted(
                items.values(), key=operator.attrgetter('sortkey'))]
            classdict['sort_order'] = tuple(sort_order)
        # Assign new sortkey values from zero.
        sorted_items = []
        for sort_id, item_name in enumerate(sort_order):
            item = classdict[item_name]
            item.sortkey = sort_id
            sorted_items.append(item)
        return sorted_items

    def __new__(cls, classname, bases, classdict):
        """Called when defining a new class."""

        cls._enforceSingleInheritance(classname, bases, classdict)
        cls._updateClassDictWithBaseItems(bases, classdict)
        cls._updateClassDictWithTemplateItems(classdict)

        items = [(key, value) for key, value in classdict.iteritems()
                 if isinstance(value, BaseItem)]

        cls._enforceItemClassAndName(items, classname, classdict['__module__'])

        mapping = cls._generateItemMapping(items)
        sorted_items = cls._enforceSortOrder(classname, classdict, items)

        classdict['items'] = EnumItems(sorted_items, mapping)
        classdict['name'] = classname
        classdict['description'] = classdict.get('__doc__', None)

        global enumerated_type_registry
        if classname in enumerated_type_registry:
            other = enumerated_type_registry[classname]
            raise TypeError(
                'An enumerated type already exists with the name %s (%s.%s).'
                % (classname, other.__module__, other.name))

        instance = type.__new__(cls, classname, bases, classdict)

        # Add a reference to the enumerated type to each item.
        for item in instance.items:
            item.enum = instance

        # Add the enumerated type to the registry.
        enumerated_type_registry[classname] = instance

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


class MetaEnum(BaseMetaEnum):
    """The metaclass for `EnumeratedType`."""
    item_type = Item
    enum_name = 'EnumeratedType'

    def __repr__(self):
        return "<EnumeratedType '%s'>" % self.name


class MetaDBEnum(BaseMetaEnum):
    """The meta class for `DBEnumeratedType`.

    Provides a method for getting the item based on the database identifier in
    addition to all the normal enumerated type methods.
    """
    item_type = DBItem
    enum_name = 'DBEnumeratedType'

    @classmethod
    def _generateItemMapping(cls, items):
        """DBEnumeratedTypes also map the database value of the DBItem to the
        item instance."""
        mapping = BaseMetaEnum._generateItemMapping(items)
        for item_name, item in items:
            # If the value is already in the mapping then we have two
            # different items attempting to map the same number.
            if item.value in mapping:
                # We really want to provide the names in alphabetical order.
                args = [item.value] + sorted(
                    [item_name, mapping[item.value].name])
                raise TypeError(
                    'Two DBItems with the same value %s (%s, %s)'
                    % tuple(args))
            else:
                mapping[item.value] = item
        return mapping

    def __repr__(self):
        return "<DBEnumeratedType '%s'>" % self.name


class EnumeratedType:
    """An enumeration of items.

    The items of the enumeration must be instances of the class `Item`.
    These items are accessible through a class attribute `items`.  The ordering
    of the items attribute is the same order that the items are defined in the
    class.

    A `sort_order` attribute can be defined to override the default ordering.
    The sort_order should contain the names of the all the items in the
    ordering that is desired.
    """
    __metaclass__ = MetaEnum


class DBEnumeratedType:
    """An enumeration with additional mapping from an integer to `Item`.

    The items of a class inheriting from DBEnumeratedType must be of type
    `DBItem`.
    """
    __metaclass__ = MetaDBEnum


def use_template(enum_type, include=None, exclude=None):
    """An alternative way to extend an enumerated type other than inheritance.

    The parameters include and exclude should either be the name values of the
    items (the parameter names), or a list or tuple that contains string
    values.
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

    template_items = []
    for item in items:
        if item.name not in exclude:
            template_items.append(item)

    locals['template_items'] = template_items
