# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Implementation classes for config."""

__metaclass__ = type

__all__ = [
    'Config',
    'ConfigData',
    'ConfigSchema',
    'ImplicitTypeSchema',
    'ImplicitTypeSection',
    'Section',
    'SectionSchema',]

from ConfigParser import NoSectionError, RawConfigParser
import copy
from os.path import abspath, basename, dirname
import re
import StringIO

from zope.interface import implements

from canonical.lazr.interfaces import (
    ConfigErrors, ICategory, IConfigData, IConfigLoader, IConfigSchema,
    InvalidSectionNameError, ISection, ISectionSchema, IStackableConfig,
    NoCategoryError, NoConfigError, RedefinedSectionError, UnknownKeyError,
    UnknownSectionError)
from canonical.lazr.decorates import decorates


def read_content(filename):
    """Return the content of a file at filename as a string."""
    source_file = open(filename, 'r')
    try:
        raw_data = source_file.read()
    finally:
        source_file.close()
    return raw_data


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

    @property
    def category_and_section_names(self):
        """See `ISectionSchema`."""
        if '.' in self.name:
            return tuple(self.name.split('.'))
        else:
            return (None, self.name)


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

    def __getattr__(self, name):
        """See `ISection`."""
        if name in self._options:
            return self._options[name]
        else:
            raise AttributeError(
                "No section key named %s." % name)

    @property
    def category_and_section_names(self):
        """See `ISection`."""
        return self.schema.category_and_section_names

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

    def clone(self):
        """Return a copy of this section.

        The extension mechanism requires a copy of a section to prevent
        mutation.
        """
        return copy.deepcopy(self)


class ImplicitTypeSection(Section):
    """See `ISection`.

    ImplicitTypeSection supports implicit conversion of key values to
    simple datatypes. It accepts the same section data as Section; the
    datatype information is not embedded in the schema or the config file.
    """
    re_types = re.compile(r'''
        (?P<false> ^false$) |
        (?P<true> ^true$) |
        (?P<none> ^none$) |
        (?P<int> ^[+-]?\d+$) |
        (?P<str> ^.*)
        ''', re.IGNORECASE | re.VERBOSE)

    def _convert(self, value):
        """Return the value as the datatype the str appears to be.

        Conversion rules:
        * bool: a single word, 'true' or 'false', case insensitive.
        * int: a single word that is a number. Signed is supported,
            hex and octal numbers are not.
        * str: anything else.
        """
        match = self.re_types.match(value)
        if match.group('false'):
            return False
        elif match.group('true'):
            return True
        elif match.group('none'):
            return None
        elif match.group('int'):
            return int(value)
        else:
            # match.group('str'); just return the value.
            return value

    def __getitem__(self, key):
        """See `ISection`."""
        value = super(ImplicitTypeSection, self).__getitem__(key)
        return self._convert(value)

    def __getattr__(self, name):
        """See `ISection`."""
        value = super(ImplicitTypeSection, self).__getattr__(name)
        return self._convert(value)


class ConfigSchema:
    """See `IConfigSchema`."""
    implements(IConfigSchema, IConfigLoader)

    _section_factory = Section

    def __init__(self, filename):
        """Load a configuration schema from the provided filename.

        :raise `UnicodeDecodeError`: if the string contains non-ascii
            characters.
        :raise `RedefinedSectionError`: if a SectionSchema name is redefined.
        :raise `InvalidSectionNameError`: if a SectionSchema name is
            ill-formed.
        """
        # XXX sinzui 2007-12-13:
        # RawConfigParser permits redefinition and non-ascii characters.
        # The raw schema data is examined before creating a config.
        self.filename = filename
        self.name = basename(filename)
        self._section_schemas = {}
        self._category_names = []
        raw_schema = self._getRawSchema(filename)
        parser = RawConfigParser()
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
        # Retrieve all the templates first because section() does not
        # follow the order of the conf file.
        for name in parser.sections():
            (section_name, category_name,
             is_template, is_optional) = self._parseSectionName(name)
            if is_template:
                templates[category_name] = dict(parser.items(name))
        for name in parser.sections():
            (section_name, category_name,
             is_template, is_optional) = self._parseSectionName(name)
            if is_template:
                continue
            options = dict(templates.get(category_name, {}))
            options.update(parser.items(name))
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
    def section_factory(self):
        """See `IConfigSchema`."""
        return self._section_factory

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
        if name not in self.category_names:
            raise NoCategoryError(name)
        section_schemas = []
        for key in self._section_schemas:
            section = self._section_schemas[key]
            category, dummy = section.category_and_section_names
            if name == category:
                section_schemas.append(section)
        return section_schemas

    def _getRequiredSections(self):
        """return a dict of `Section`s from the required `SectionSchemas`."""
        sections = {}
        for section_schema in self:
            if not section_schema.optional:
                sections[section_schema.name] = self.section_factory(
                    section_schema)
        return sections

    def load(self, filename):
        """See `IConfigLoader`."""
        conf_data = read_content(filename)
        return self._load(filename, conf_data)

    def loadFile(self, source_file, filename=None):
        """See `IConfigLoader`."""
        conf_data = source_file.read()
        if filename is None:
            filename = getattr(source_file, 'name')
            assert filename is not None, (
                'filename must be provided if the file-like object '
                'does not have a name attribute.')
        return self._load(filename, conf_data)

    def _load(self, filename, conf_data):
        """Return a Config parsed from conf_data."""
        config = Config(self)
        config.push(filename, conf_data)
        return config


class ImplicitTypeSchema(ConfigSchema):
    """See `IConfigSchema`.

    ImplicitTypeSchema creates a config that supports implicit datatyping
    of section key values.
    """

    _section_factory = ImplicitTypeSection


class ConfigData:
    """See `IConfigData`."""
    implements(IConfigData)

    def __init__(self, filename, sections, extends=None, errors=None):
        """Set the configuration data."""
        self.filename = filename
        self.name = basename(filename)
        self._sections = sections
        self._category_names = self._getCategoryNames()
        self._extends = extends
        if errors is None:
            self._errors = []
        else:
            self._errors = errors

    def _getCategoryNames(self):
        """Return a tuple of category names that the `Section`s belong to."""
        category_names = set()
        for section_name in self._sections:
            section = self._sections[section_name]
            category, dummy = section.category_and_section_names
            if category is not None:
                category_names.add(category)
        return tuple(category_names)

    @property
    def category_names(self):
        """See `IConfigData`."""
        return self._category_names

    def __iter__(self):
        """See `IConfigData`."""
        return self._sections.itervalues()

    def __contains__(self, name):
        """See `IConfigData`."""
        return name in self._sections.keys()

    def __getitem__(self, name):
        """See `IConfigData`."""
        try:
            return self._sections[name]
        except KeyError:
            raise NoSectionError(name)

    def getByCategory(self, name):
        """See `IConfigData`."""
        if name not in self.category_names:
            raise NoCategoryError(name)
        sections = []
        for key in self._sections:
            section = self._sections[key]
            category, dummy = section.category_and_section_names
            if name == category:
                sections.append(section)
        return sections


class Config:
    """See `IStackableConfig`."""
    # LAZR config classes may access ConfigData private data.
    # pylint: disable-msg=W0212
    implements(IStackableConfig)
    decorates(IConfigData, context='data')

    def __init__(self, schema):
        """Set the schema and configuration."""
        self._overlays = (
            ConfigData(schema.filename, schema._getRequiredSections()), )
        self.schema = schema

    def __getattr__(self, name):
        """See `IStackableConfig`."""
        if name in self.data._sections:
            return self.data._sections[name]
        elif name in self.data._category_names:
            return Category(name, self.data.getByCategory(name))
        raise AttributeError("No section or category named %s." % name)

    @property
    def data(self):
        """See `IStackableConfig`."""
        return self.overlays[0]

    @property
    def extends(self):
        """See `IStackableConfig`."""
        if len(self.overlays) == 1:
            # The ConfigData made from the schema defaults extends nothing.
            return None
        else:
            return self.overlays[1]

    @property
    def overlays(self):
        """See `IStackableConfig`."""
        return self._overlays

    def validate(self):
        """See `IConfigData`."""
        if len(self.data._errors) > 0:
            message = "%s is not valid." % self.name
            raise ConfigErrors(message, errors=self.data._errors)
        return True

    def push(self, conf_name, conf_data):
        """See `IStackableConfig`.

        Create a new ConfigData object from the raw conf_data, and
        place it on top of the overlay stack. If the conf_data extends
        another conf, a ConfigData object will be created for that first.
        """
        confs = self._getExtendedConfs(conf_name, conf_data)
        confs.reverse()
        for conf_name, parser, encoding_errors in confs:
            config_data = self._createConfigData(
                conf_name, parser, encoding_errors)
            self._overlays = (config_data, ) + self._overlays

    def _getExtendedConfs(self, conf_filename, conf_data, confs=None):
        """Return a list of 3-tuple(conf_name, parser, encoding_errors).

        :param conf_filename: The path and name the conf file.
        :param conf_data: Unparsed config data.
        :param confs: A list of confs that extend filename.
        :return: A list of confs ordered from extender to extendee.
        :raises IOError: If filename cannot be read.

        This method parses the config data and checks for encoding errors.
        It checks parsed config data for the extends key in the meta section.
        It reads the unparsed config_data from the extended filename.
        It passes filename, data, and the working list to itself.
        """
        if confs is None:
            confs = []
        encoding_errors = self._verifyEncoding(conf_data)
        parser = RawConfigParser()
        parser.readfp(StringIO.StringIO(conf_data), conf_filename)
        confs.append((conf_filename, parser, encoding_errors))
        if parser.has_option('meta', 'extends'):
            base_path = dirname(conf_filename)
            extends_name = parser.get('meta', 'extends')
            extends_filename = abspath('%s/%s' % (base_path, extends_name))
            extends_data = read_content(extends_filename)
            self._getExtendedConfs(extends_filename, extends_data, confs)
        return confs

    def _createConfigData(self, conf_name, parser, encoding_errors):
        """Return a new ConfigData object created from a parsed conf file.

        :param conf_name: the full name of the config file, may be a filepath.
        :param parser: the parsed config file; an instance of ConfigParser.
        :param encoding_errors: a list of encoding error in the config file.
        :return: a new ConfigData object.

        This method extracts the sections, keys, and values from the parser
        to construct a new ConfigData object The list of encoding errors are
        incorporated into the the list of data-related errors for the
        ConfigData.
        """
        sections = {}
        for section in self.data:
            sections[section.name] = section.clone()
        errors = list(self.data._errors)
        errors.extend(encoding_errors)
        extends = None
        for section_name in parser.sections():
            if section_name == 'meta':
                extends, meta_errors = self._loadMetaData(parser)
                errors.extend(meta_errors)
                continue
            if (section_name.endswith('.template')
                or section_name.endswith('.optional')):
                # This section is a schema directive.
                continue
            if section_name not in self.schema:
                # Any section not in the the schema is an error.
                msg = "%s does not have a %s section." % (
                    self.schema.name, section_name)
                errors.append(UnknownSectionError(msg))
                continue
            if section_name not in self.data:
                # Create the optional section from the schema.
                section_schema = self.schema[section_name]
                sections[section_name] = self.schema.section_factory(
                    section_schema)
            # Update the section with the parser options.
            items = parser.items(section_name)
            section_errors = sections[section_name].update(items)
            errors.extend(section_errors)
        return ConfigData(conf_name, sections, extends, errors)

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

    def _loadMetaData(self, parser):
        """Load the config meta data from the ConfigParser.

        The meta section is reserved for the LAZR config parser.

        :return: a list of errors if there are errors, or an empty list.
        """
        extends = None
        errors = []
        for key in parser.options('meta'):
            if key == "extends":
                extends = parser.get('meta', 'extends')
            else:
                # Any other key is an error.
                msg = "The meta section does not have a %s key." % key
                errors.append(UnknownKeyError(msg))
        return (extends, errors)

    def pop(self, conf_name):
        """See `IStackableConfig`."""
        index = self._getIndexOfOverlay(conf_name)
        removed_overlays = self.overlays[:index]
        self._overlays = self.overlays[index:]
        return removed_overlays

    def _getIndexOfOverlay(self, conf_name):
        """Return the index of the config named conf_name.

        The bottom of the stack cannot never be returned because it was
        made from the schema.
        """
        schema_index = len(self.overlays) - 1
        for index, config_data in enumerate(self.overlays):
            if index == schema_index and config_data.name == conf_name:
                raise NoConfigError("Cannot pop the schema's default config.")
            if config_data.name == conf_name:
                return index + 1
        # The config data was not found in the overlays.
        raise NoConfigError('No config with name: %s.' % conf_name)


class Category:
    """See `ICategory`."""
    implements(ICategory)

    def __init__(self, name, sections):
        """Initialize the Category its name and a list of sections."""
        self.name = name
        self._sections = {}
        for section in sections:
            self._sections[section.name] = section

    def __getattr__(self, name):
        """See `ICategory`."""
        full_name = "%s.%s" % (self.name, name)
        if full_name in self._sections:
            return self._sections[full_name]
        raise AttributeError("No section named %s." % name)
