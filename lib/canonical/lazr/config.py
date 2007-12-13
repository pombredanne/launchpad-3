# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Implementation classes for config."""

__metaclass__ = type

__all__ = [
    'ConfigSchema',
    'SectionSchema',]

import os
from ConfigParser import SafeConfigParser

from zope.interface import implements

from canonical.lazr.interfaces import ISectionSchema, IConfigSchema


class ConfigSchema(object):
    """See `IConfigSchema`."""
    implements(IConfigSchema)

    def __init__(self, filename):
        """See `IConfigSchema`."""
        config = SafeConfigParser()
        config.readfp(open(filename))
        self._section_schemas = self._parseSectionSchemas(config)
        self.filename = filename
        self.name = os.path.basename(filename)

    def _parseSectionSchemas(self, config):
        """Return a list of SectionSchemas from the config."""
        section_schemas = []
        # Template sections define default options for categories. They are
        # copied to each SectionSchema that belong to the category.        
        templates = {}
        for name in config.sections():
            (section_name, category_name,
             is_template, is_optional) = self._parseSectionName(name)
            options = templates.get(category_name, {})
            options.update(config.items(name))
            if is_template:
                templates[category_name] = options
            else:
                section_schemas.append(
                    SectionSchema(section_name, options, is_optional))
        return section_schemas

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
            raise SyntaxError, (message % name)
        if dots == 1:
            category_name, process_name = section_name.split('.')
            if process_name == 'template':
                is_template = True
                section_name = category_name
        return (section_name, category_name,  is_template, is_optional)

    @property
    def category_names(self):
        """See `IConfigSchema`."""

    def __iter__(self):
        """See `IConfigSchema`."""
        for section_schema in self._section_schemas:
            yield section_schema

    def __contains__(self, name):
        """See `IConfigSchema`."""

    def __getitem__(self, name):
        """See `IConfigSchema`."""

    def getByCategory(self, name):
        """See `IConfigSchema`."""


class SectionSchema(object):
    """See `ISectionSchema`."""
    implements(ISectionSchema)

    def __init__(self, name, options, is_optional=False):
        """See `ISectionSchema`"""
        self.name = name
        self._options = options
