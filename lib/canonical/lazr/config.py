# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Implementation classes for config."""

__metaclass__ = type

__all__ = [
    'Config',
    'ConfigSchema',
    'Section',
    'SectionSchema',]

from ConfigParser import NoSectionError, SafeConfigParser
import os
import re
import StringIO

from zope.interface import implements

from canonical.lazr.interfaces import (
    ConfigSchemaError, IConfig, IConfigLoader, IConfigSchema,
    InvalidSectionNameError, ISection, ISectionSchema, NoCategoryError,
    RedefinedSectionError)


def read_raw_data(file_path):
    """Return the content of a file at file_path as a string."""
    source_file = open(file_path, 'r')
    try:
        raw_data = source_file.read()
    finally:
        source_file.close()
    return raw_data


class ConfigSchema(object):
    """See `IConfigSchema`."""
    implements(IConfigSchema, IConfigLoader)

    def __init__(self, filename):
        """Load a configuration schema from the provided filename.

        :raise `UnicodeDecodeError`: if the string contains non-ascii
            characters.
        :raise `RedefinedSectionError`: if a SectionSchema name is redefined.
        :raise `InvalidSectionNameError`: if a SectionSchema name is
            ill-formed.
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

    def _getRawSchema(self, file_path):
        """Return the contents of the schema at file_path as a StringIO."""
        raw_schema = read_raw_data(file_path)
        self._verifyRawData(raw_schema)
        return StringIO.StringIO(raw_schema)

    def _verifyRawData(self, raw_data):
        """Verify that the unparsed schema is good to parse.

        This method verifies that the file is ascii encoded and that no
        section name is redefined.
        """
        # Verify that the string is ascii.
        raw_data.encode('ascii', 'ignore')
        # Verify that no sections are redefined.
        section_names = []
        for section_name in re.findall(
                r'^\s*\[[^\]]+\]', raw_data, re.M):
            if section_name in section_names:
                raise RedefinedSectionError(section_name)
            else:
                section_names.append(section_name)

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

    _section_name_pattern = re.compile(r'\w[\w.-]+\w')

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
            # Example: [name.optional] or [category.template]
            del name_parts[-1]
        count = len(name_parts)
        if count == 1 and is_template:
            # Example: [category.template]
            category_name = name_parts[0]
            section_name = name_parts[0]
        elif count == 1:
            # Example: [name]
            category_name = None
            section_name = name_parts[0]
        elif count == 2:
            # Example: [category.name]
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

    def load(self, file_path):
        """See `IConfigLoader`."""
        config_data = read_raw_data(file_path)
        return Config(file_path, config_data, self)

    def loadFile(self, source_file, filename=None):
        """See `IConfigLoader`."""
        config_data = source_file.read()
        if filename is None:
            filename = source_file.name
        return Config(filename, config_data, self)


class Config(object):
    """see `IConfig`."""
    implements(IConfig)

    def __init__(self, filename, config_data, schema):
        """Set the schema and configuration."""
        self.filename = filename
        self.name = os.path.basename(filename)
        self.schema = schema
        self._extends = None
        self._errors = []
        self._verifyEncoding(config_data)
        parser = SafeConfigParser()
        parser.readfp(StringIO.StringIO(config_data), filename)
        self._setSectionsAndCategoriesNames(parser)

    def _verifyEncoding(self, config_data):
        """Verify the data encoding and store any errors."""
        try:
            config_data.encode('ascii', 'ignore')
        except UnicodeDecodeError, error:
            self._errors.append(error)

    def _setSectionsAndCategoriesNames(self, parser):
        """Set the Sections and category_names from the schema and parser."""
        sections = {}
        for section_schema in self.schema:
            if not section_schema.optional:
                sections[section_schema.name] = Section(section_schema)
        for section_name in parser.sections():
            if section_name == 'meta':
                self._extends = parser.get(section_name, 'extends')
                # XXX sinzui 2007-12-18: Any other option is an error.
                continue
            if section_name not in self.schema:
                # XXX sinzui 2007-12-18: Any other section is an error.
                continue
            if section_name not in sections:
                # Retrieve the optional section from the schema.
                section_schema = self.schema[section_name]
                sections[section_name] = Section(section_schema)
            sections[section_name]._options.update(parser.items(section_name))
            # XXX sinzui 2007-12-18: Any extra options is an error.
        self._sections = sections
        category_names = set()
        for section_name in sections:
            if '.' in section_name:
                category_names.add(section_name.split('.')[0])
        self._category_names = list(category_names)

    @property
    def extends(self):
        """See `IConfig`."""
        return self._extends

    @property
    def category_names(self):
        """See `IConfig`."""
        return self._category_names

    def __iter__(self):
        """See `IConfig`."""
        return self._sections.itervalues()

    def __contains__(self, name):
        """See `IConfig`."""
        return name in self._sections.keys()

    def __getitem__(self, name):
        """See `IConfig`."""
        try:
            return self._sections[name]
        except KeyError:
            raise NoSectionError(name)

    def getByCategory(self, name):
        """See `IConfig`."""
        sections = []
        for key in self._sections:
            if key.startswith(name):
                sections.append(self._sections[key])
        if len(sections) == 0:
            raise NoCategoryError(name)
        return sections

    def validate(self):
        """See `IConfig`."""
        if len(self._errors) > 0:
            error = ConfigSchemaError("%s is not valid" % self.name)
            error.errors = self._errors
            raise error
        return True


class SectionSchema(object):
    """See `ISectionSchema`."""
    implements(ISectionSchema)

    def __init__(self, name, options, is_optional=False):
        """Create an `ISectionSchema` from the name and options.

        :param name: A string. The name of the ISectionSchema.
        :param options: A dict of the key-value pairs in the ISectionSchema.
        :param is_optional: A boolean. Is this section schema optional?
        :raise `RedefinedKeyError`: if a keys is redefined in SectionSchema.
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


class Section(object):
    """See `ISection`."""
    implements(ISection)

    def __init__(self, schema):
        """Create an `ISection` from schema.

        :param schema: The ISectionSchema that defines this ISection.
        """
        self.schema = schema
        self.name = schema.name
        self.optional = schema.optional
        self._options = dict(schema._options)

    def __iter__(self):
        """See `ISection`"""
        return self._options.iterkeys()

    def __contains__(self, name):
        """See `ISection`"""
        return name in self._options

    def __getitem__(self, key):
        """See `ISection`"""
        return self._options[key]

    def get(self, key, default=None):
        """See `ISection`."""
        if key in self._options:
            return self._options[key]
        else:
            return default
