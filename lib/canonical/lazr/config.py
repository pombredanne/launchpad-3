# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Implementation classes for config."""

__metaclass__ = type

__all__ = [
    'ConfigSchema',
    'SectionSchema',]

from ConfigParser import SafeConfigParser, NoSectionError
import os
import re
import StringIO

from zope.interface import implements

from canonical.lazr.interfaces import ISectionSchema, IConfigSchema


class RedefinedKeyError(SyntaxError):
    """A key in a section cannot be redefined."""


class RedefinedSectionError(SyntaxError):
    """A section in a config file cannot be redefined."""


class MultipleCategoriesError(SyntaxError):
    """The section name contains more than one category."""


class NoCategoryError(LookupError):
    """No SchemaSections belong to the category name."""


class ConfigSchema(object):
    """See `IConfigSchema`."""
    implements(IConfigSchema)

    def __init__(self, filename):
        """See `IConfigSchema`."""
        # XXX sinzui 2007-12-13:
        # SafeConfigParser permits redefinition and non-ascii characters.
        # The raw schema data is examined before creating a config.
        raw_schema = self._getRawSchema(filename)
        config = SafeConfigParser()
        config.readfp(raw_schema, filename)
        self._setSectionSchemasAndCategoriesNames(config)
        self.filename = filename
        self.name = os.path.basename(filename)

    def _getRawSchema(self, filename):
        """Return the contents of the schema file as a StringIO.

        This method verifies that the file is ascii encoded and that no
        section name is refined.
        """
        schema_file = open(filename, 'r')
        raw_schema = schema_file.read()
        schema_file.close()
        # Verify that the string is ascii.
        raw_schema.encode('ascii', 'ignore')
        # Verify that no sections are redefined.
        section_names = []
        for section_name in re.findall(r'^\s*\[[^\]]+\]', raw_schema, re.M):
            if section_name in section_names:
                raise RedefinedSectionError, section_name
            else:
                section_names.append(section_name)
        return StringIO.StringIO(raw_schema)

    def _setSectionSchemasAndCategoriesNames(self, config):
        """Set the SectionSchemas and category_names from the config."""
        section_schemas = {}
        category_names = set()
        templates = {}
        for name in config.sections():
            (section_name, category_name,
             is_template, is_optional) = self._parseSectionName(name)
            options = templates.get(category_name, {})
            options.update(config.items(name))
            if is_template:
                templates[category_name] = options
            else:
                section_schemas[section_name] = SectionSchema(
                    section_name, options, is_optional)
            if category_name is not None:
                category_names.add(category_name)
        self._category_name = list(category_names)
        self._section_schemas = section_schemas

    def _parseSectionName(self, name):
        """Return a 4-tuple of names and kinds embedded in the name.

        :return: (section_name, category_name, is_template, is_optional).
            section_name is always a string. category_name is a string or
            None if there is no prefix. is_template and is_optional
            are False by default, but will be true if the name's suffix
            ends in '.template' or '.optional'.
        """
        section_name = name
        category_name = None
        is_template = False
        is_optional = False
        if name.endswith('.optional'):
            is_optional = True
            section_name = name[0:-len('.optional')]
        # After the removal of the 'optional' suffix, the section name
        # may have a category prefix or a 'template' suffix.
        dots = section_name.count('.')
        if dots > 1:
            message = 'The section [%s] belongs to more than one category.'
            raise MultipleCategoriesError, (message % name)
        if dots == 1:
            category_name, process_name = section_name.split('.')
            if process_name == 'template':
                is_template = True
                section_name = category_name
        return (section_name, category_name,  is_template, is_optional)

    @property
    def category_names(self):
        """See `IConfigSchema`."""
        return self._category_name

    def __iter__(self):
        """See `IConfigSchema`."""
        return self._section_schemas.itervalues()

    def __contains__(self, name):
        """See `IConfigSchema`."""
        return name in self._section_schemas.keys()

    def __getitem__(self, name):
        """See `IConfigSchema`."""
        try:
            return self._section_schemas[name]
        except KeyError:
            raise NoSectionError, name

    def getByCategory(self, name):
        """See `IConfigSchema`."""
        section_schemas = []
        for key in self._section_schemas:
            if key.startswith(name):
                section_schemas.append(self._section_schemas[key])
        if len(section_schemas) == 0:
            raise NoCategoryError, name
        return section_schemas


class SectionSchema(object):
    """See `ISectionSchema`."""
    implements(ISectionSchema)

    def __init__(self, name, options, is_optional=False):
        """See `ISectionSchema`"""
        # This method should raise RedefinedKeyError if the schema file
        # redefines a key, but SafeConfigParser swallows redefined keys.
        self.name = name
        self._options = options
        self.optional = is_optional

    def __iter__(self):
        """See `ISectionSchema`"""
        return self._options.iterkeys()

    def __contains__(self, name):
        """See `ISectionSchema`"""
        return name in self._options.keys()

    def __getitem__(self, key):
        """See `ISectionSchema`"""
        return self._options[key]
