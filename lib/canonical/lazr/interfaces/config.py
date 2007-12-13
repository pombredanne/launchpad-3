# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213
"""Interfaces for process configuration.."""

__metaclass__ = type

__all__ = [
    'IConfigSchema',
    'IConfigSchemaParser',
    'ISectionSchema',]

from zope.interface import Interface, Attribute


class ISectionSchema(Interface):
    """A group of key-value pairs that configure a process."""
    name = Attribute("The section schema name.")

    def __init__(name, options, is_optional=False):
        """Create an ISectionSchema from the name and options.

        :param name: A string. The name of the ISectionSchema.
        :param options: A dict of the key-value pairs in the ISectionSchema.
        :param is_optional: A boolean. Is this section schema optional?
        """

    def __iter__():
        """Iterate over the keys."""

    def __contains__(name):
        """Return True or False if name is a key."""

    def __getitem__(key):
        """Return the value of the key.

        :raises KeyError: if the key does not exist.
        """


class IConfigSchema(Interface):
    """A process configuration schema.

    The config file contains sections defined by square bracket ([]).
    The section name may be divided into major and minor categories using a
    dot (.). Beneath each section is a list of key-value pairs, separated
    by a colon (:). Multiple sections with the same major category may have
    their keys defined in a section that declares it is the '.template'
    minor category. A section with '.optional' minor category is used to
    define a process that is not required. Lines that start with a hash (#)
    are comments.
    """
    name = Attribute('The basename of the config filename.')
    filename = Attribute('The path to config file')
    category_names = Attribute('The list of section category names.')

    def __init__(filename):
        """Load a configuration schema from the provided filename."""

    def __iter__():
        """Iterate over the SectionSchema."""

    def __contains__(name):
        """Return True or False if the name matches a SectionSchema."""

    def __getitem__(name):
        """Return the SchemaSection with the matching name.

        :raises NoSectionError: if the no SchemaSection has the name.
        """

    def getByCategory(name):
        """Return a list of SectionSchemas that belong to the category name.

        Section names may be made from a category name and a process name,
        separated by a dot (.). The category is synonymous with a arbitrary
        resource such as a database or a vhost. Thus database.bugs and
        database.answers are two processes that both use the database
        resource.

        :raises CategoryNotFound: if no sections have a name that starts
            with the category name.
        """

class IConfigSchemaParser(Interface):
    """A process configuration file parser.

    XXX sinzui 2007-12-12:
    We may not need this. Less is more.
    """

    def __init__(filename):
        """Load a schema from the provided filename."""
