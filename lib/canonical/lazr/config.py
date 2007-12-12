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
        parser = SafeConfigParser()
        parsed_files = parser.readfp(open(filename))
        self.filename = filename
        self.name = os.path.basename(filename)
