# Copyright 2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213
"""Interfaces for process configuration.."""

__metaclass__ = type

__all__ = [
    'ConfigSchemaError',
    'IConfig',
    'IConfigLoader',
    'IConfigSchema',
    'InvalidSectionNameError',
    'ISection',
    'ISectionSchema',
    'NoCategoryError',
    'RedefinedKeyError',
    'RedefinedSectionError',
    'UnknownKeyError',
    'UnknownSectionError']

from zope.interface import Interface, Attribute


class ConfigSchemaError(Exception):
    """A base class of all `IConfigSchema` errors."""


class RedefinedKeyError(ConfigSchemaError):
    """A key in a section cannot be redefined."""


class RedefinedSectionError(ConfigSchemaError):
    """A section in a config file cannot be redefined."""


class InvalidSectionNameError(ConfigSchemaError):
    """The section name contains more than one category."""


class NoCategoryError(LookupError):
    """No `ISectionSchema`s belong to the category name."""


class UnknownSectionError(ConfigSchemaError):
    """The config has a section that is not in the schema."""


class UnknownKeyError(ConfigSchemaError):
    """The section has a key that is not in the schema."""


class ISectionSchema(Interface):
    """Defines the valid keys and default values for a configuration group."""
    name = Attribute("The section name.")
    optional = Attribute("Is the section optional in the config?")

    def __iter__():
        """Iterate over the keys."""

    def __contains__(name):
        """Return True or False if name is a key."""

    def __getitem__(key):
        """Return the default value of the key.

        :raise `KeyError`: if the key does not exist.
        """


class ISection(ISectionSchema):
    """Defines the values for a configuration group."""
    schema = Attribute("The ISectionSchema that defines this ISection.")

    def get(key, default=None):
        """Return the value of the key, or default if key does not exist."""


class IConfigLoader(Interface):
    """A configuration file loader."""

    def load(file_path):
        """Load a configuration from the file at file_path."""

    def loadFile(source_file, filename=None):
        """Load a configuration from the open source_file.

        :param source_file: A file-like object that supports read() and
            readline()
        :param filename: The name of the configuration. If filename is None,
            The name will be taken from source_file.name.
        """


class IConfigSchema(Interface):
    """A process configuration schema.

    The config file contains sections enclosed in square brackets ([]).
    The section name may be divided into major and minor categories using a
    dot (.). Beneath each section is a list of key-value pairs, separated
    by a colon (:). Multiple sections with the same major category may have
    their keys defined in another section that appends the '.template'
    suffix to the category name. A section with '.optional' suffix is not
    required. Lines that start with a hash (#) are comments.
    """
    name = Attribute('The basename of the config filename.')
    filename = Attribute('The path to config file')
    category_names = Attribute('The list of section category names.')

    def __iter__():
        """Iterate over the `ISectionSchema`s."""

    def __contains__(name):
        """Return True or False if the name matches a `ISectionSchema`."""

    def __getitem__(name):
        """Return the `ISectionSchema` with the matching name.

        :raise `NoSectionError`: if the no ISectionSchema has the name.
        """

    def getByCategory(name):
        """Return a list of ISectionSchemas that belong to the category name.

        ISectionSchema names may be made from a category name and a group
        name, separated by a dot (.). The category is synonymous with a
        arbitrary resource such as a database or a vhost. Thus database.bugs
        and database.answers are two sections that both use the database
        resource.

        :raise `CategoryNotFound`: if no sections have a name that starts
            with the category name.
        """


class IConfig(IConfigSchema):
    """A process configuration.

    See `IConfigSchema` for more information about the config file format.
    """
    extends = Attribute("The configuration that this extends.")

    def validate():
        """Return True if the config is valid for the schema.

        :raise `ConfigSchemaError`: if the are errors. A list of all schema
            problems can be retrieved via the errors property.
        """
