# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Implementation classes for config."""

__metaclass__ = type

__all__ = [
    'ConfigSchema',
    'SectionSchema',]

from ConfigParser import NoSectionError, SafeConfigParser
import os
import re
import StringIO

from zope.interface import implements

from canonical.lazr.interfaces import (
    IConfigSchema, InvalidSectionNameError, ISectionSchema,
    NoCategoryError, RedefinedSectionError)


class ConfigSchema(object):
    """See `IConfigSchema`."""
    implements(IConfigSchema)

    def __init__(self, filename):
        """Load a configuration schema from the provided filename.

        :raises UnicodeDecodeError: if the string contains non-ascii
            characters.
        :raises RedefinedSectionError: if a SectionSchema name is redefined.
        """
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
        section name is redefined.
        """
        schema_file = open(filename, 'r')
        try:
            raw_schema = schema_file.read()
        finally:
            schema_file.close()
        # Verify that the string is ascii.
        raw_schema.encode('ascii', 'ignore')
        # Verify that no sections are redefined.
        section_names = []
        for section_name in re.findall(r'^\s*\[[^\]]+\]', raw_schema, re.M):
            if section_name in section_names:
                raise RedefinedSectionError(section_name)
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
            options = dict(templates.get(category_name, {}))
            options.update(config.items(name))
            if is_template:
                templates[category_name] = options
            else:
                section_schemas[section_name] = SectionSchema(
                    section_name, options, is_optional)
            if category_name is not None:
                category_names.add(category_name)
        self._category_names = list(category_names)
        self._section_schemas = section_schemas

    _section_name_pattern = re.compile(r'[\w.-]+')

    def _parseSectionName(self, name):
        """Return a 4-tuple of names and kinds embedded in the name.

        :return: (section_name, category_name, is_template, is_optional).
            section_name is always a string. category_name is a string or
            None if there is no prefix. is_template and is_optional
            are False by default, but will be true if the name's suffix
            ends in '.template' or '.optional'.
        """
        name_parts = name.split('.')
        is_template = name_parts[-1] == 'template'
        is_optional = name_parts[-1] == 'optional'
        if is_template or is_optional:
            # The suffix is not a part of the section name.
            del name_parts[-1]
        count = len(name_parts)
        if count == 1 and is_template:
            category_name = name_parts[0]
            section_name = name_parts[0]
        elif count == 1:
            category_name = None
            section_name = name_parts[0]
        elif count == 2:
            category_name = name_parts[0]
            section_name = '.'.join(name_parts)
        else:
            raise InvalidSectionNameError('[%s] has too many parts.' % name)
        if self._section_name_pattern.match(section_name) is None:
            raise InvalidSectionNameError(
                '[%s] name does not match [\w.-]+.' % name)
        return (section_name, category_name,  is_template, is_optional)

    @property
    def category_names(self):
        """See `IConfigSchema`."""
        return self._category_names

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
            raise NoSectionError(name)

    def getByCategory(self, name):
        """See `IConfigSchema`."""
        section_schemas = []
        for key in self._section_schemas:
            if key.startswith(name):
                section_schemas.append(self._section_schemas[key])
        if len(section_schemas) == 0:
            raise NoCategoryError(name)
        return section_schemas


class SectionSchema(object):
    """See `ISectionSchema`."""
    implements(ISectionSchema)

    def __init__(self, name, options, is_optional=False):
        """Create an ISectionSchema from the name and options.

        :param name: A string. The name of the ISectionSchema.
        :param options: A dict of the key-value pairs in the ISectionSchema.
        :param is_optional: A boolean. Is this section schema optional?
        :raises RedefinedKeyError: if a keys is redefined in SectionSchema.
        """
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
        return name in self._options

    def __getitem__(self, key):
        """See `ISectionSchema`"""
        return self._options[key]
