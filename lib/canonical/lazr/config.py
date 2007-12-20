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
    ConfigErrors, IConfig, IConfigLoader, IConfigSchema,
    InvalidSectionNameError, ISection, ISectionSchema, NoCategoryError,
    RedefinedSectionError, UnknownKeyError, UnknownSectionError)
from canonical.lp import decorates


def read_content(filename):
    """Return the content of a file at filename as a string."""
    source_file = open(filename, 'r')
    try:
        raw_data = source_file.read()
    finally:
        source_file.close()
    return raw_data


class ConfigSchema:
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
        self.filename = filename
        self.name = os.path.basename(filename)
        self._section_schemas = {}
        self._category_names = []
        raw_schema = self._getRawSchema(filename)
        parser = SafeConfigParser()
        parser.readfp(raw_schema, filename)
        self._setSectionSchemasAndCategoryNames(parser)


    def _getRawSchema(self, filename):
        """Return the contents of the schema at filename as a StringIO.

        This method verifies that the file is ascii encoded and that no
        section name is redefined.
        """
        raw_schema = read_content(filename)
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

    def _setSectionSchemasAndCategoryNames(self, parser):
        """Set the SectionSchemas and category_names from the config."""
        category_names = set()
        templates = {}
        for name in parser.sections():
            (section_name, category_name,
             is_template, is_optional) = self._parseSectionName(name)
            options = dict(templates.get(category_name, {}))
            options.update(parser.items(name))
            if is_template:
                templates[category_name] = options
            else:
                self._section_schemas[section_name] = SectionSchema(
                    section_name, options, is_optional)
            if category_name is not None:
                category_names.add(category_name)
        self._category_names = list(category_names)

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

    def load(self, filename):
        """See `IConfigLoader`."""
        config_data = read_content(filename)
        return Config(filename, config_data, self)

    def loadFile(self, source_file, filename=None):
        """See `IConfigLoader`."""
        config_data = source_file.read()
        if filename is None:
            filename = getattr(source_file, 'name')
            assert filename is not None, (
                'filename must be provided if the file-like object '
                'does not have a name attribute.')
        return Config(filename, config_data, self)


class Config:
    """see `IConfig`."""
    implements(IConfig)

    def __init__(self, filename, config_data, schema):
        """Set the schema and configuration."""
        self.filename = filename
        self.name = os.path.basename(filename)
        self.schema = schema
        self._sections = self._getRequiredSectionsFromSchema()
        self._category_names = self._getCategoryNames()
        self._extends = None
        self._errors = []
        self._loadConfigData(config_data, filename)

    def _getRequiredSectionsFromSchema(self):
        """return a dict of `Section`s from the required `SectionSchemas`."""
        sections = {}
        for section_schema in self.schema:
            if not section_schema.optional:
                sections[section_schema.name] = Section(section_schema)
        return sections

    def _getCategoryNames(self):
        """Return a tuple of category names that the `Section`s belong to."""
        category_names = set()
        for section_name in self._sections:
            if '.' in section_name:
                category_names.add(section_name.split('.')[0])
        return tuple(category_names)

    def _verifyEncoding(self, config_data):
        """Verify that the data is ASCII encoded.

        :return: a list of UnicodeDecodeError errors. If there are no
            errors, return an empty list.
        """
        errors = []
        try:
            config_data.encode('ascii', 'ignore')
        except UnicodeDecodeError, error:
            errors.append(error)
        return errors

    def _loadConfigData(self, config_data, filename):
        """Set the Sections and category_names from the config data.

        New _sections, _category_names, and _errors are created from copies
        of the current objects instead of making updates. This allows
        overlaid configs to retain their state.

        :return: a list of parsing errors. If there are no errors, an empty
            list is returned.
        """
        sections = dict(self._sections)
        errors = list(self._errors)
        encoding_errors = self._verifyEncoding(config_data)
        errors.extend(encoding_errors)
        parser = SafeConfigParser()
        parser.readfp(StringIO.StringIO(config_data), filename)
        for section_name in parser.sections():
            if section_name == 'meta':
                meta_errors = self._loadMetaData(parser)
                errors.extend(meta_errors)
                continue
            if section_name not in self.schema:
                # Any section not in the the schema is an error.
                msg = "%s does not have a %s section." % (
                    self.schema.name, section_name)
                errors.append(UnknownSectionError(msg))
                continue
            if section_name not in self._sections:
                # Create the optional section from the schema.
                section_schema = self.schema[section_name]
                sections[section_name] = Section(section_schema)
            # Update the section with the parser options.
            items = parser.items(section_name)
            section_errors = sections[section_name].update(items)
            errors.extend(section_errors)
        self._sections = sections
        self._errors = errors
        self._category_names = self._getCategoryNames()

    def _loadMetaData(self, parser):
        """Load the config meta data from the ConfigParser.

        The meta section is reserved for the LAZR config parser.

        :return: a list of errors if there are errors, or an empty list.
        """
        errors = []
        for key in parser.options('meta'):
            if key == "extends":
                self._extends = parser.get('meta', 'extends')
            else:
                # Any other key is an error.
                msg = "The meta section does not have a %s key." % key
                errors.append(UnknownKeyError(msg))
        return errors

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
            error = ConfigErrors("%s is not valid" % self.name)
            error.errors = self._errors
            raise error
        return True


class SectionSchema:
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


class Section:
    """See `ISection`."""
    implements(ISection)
    decorates(ISectionSchema, context='schema')

    def __init__(self, schema):
        """Create an `ISection` from schema.

        :param schema: The ISectionSchema that defines this ISection.
        """
        self.schema = schema
        self._options = dict([(key, schema[key]) for key in schema])

    def __getitem__(self, key):
        """See `ISection`"""
        return self._options[key]

    def update(self, items):
        """Update the keys with new values.

        :return: A list of `UnknownKeyError`s if the section does not have
            the key. An empty list is returned if there are no errors.
        """
        errors = []
        for key, value in items:
            if key in self._options:
                self._options[key] = value
            else:
                msg = "%s does not have a %s key." % (self.name, key)
                errors.append(UnknownKeyError(msg))
        return errors
