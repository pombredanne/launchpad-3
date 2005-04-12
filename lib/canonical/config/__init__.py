# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import sys, os, os.path
import zope.thread
import ZConfig

class BaseConfig(object):
    """A tree of these objects is used to build the config.

    Attributes are used to store items and subtrees.
    """
    def __init__(self, config):
        self.config = config

class CanonicalConfig(object):
    """
    Singleton configuration, accessed via the `config` module global.

    Cached copies are kept in thread locals ensuring the configuration
    is thread safe (not that this will be a problem if we stick with
    simple configuration).

    >>> from canonical.config import config
    >>> config.dbhost is None
    True
    >>> config.launchpad.dbuser
    'launchpad'
    >>> config.librarian.dbuser
    'librarian'
    >>> config.librarian.upload_host
    'localhost'
    >>> config.librarian.upload_port
    59090
    >>> config.librarian.download_host
    'localhost'
    >>> config.librarian.download_port
    58000

    There are also some automatically generated config items

    >>> import os.path, canonical
    >>> os.path.join(config.root, 'lib', 'canonical') == os.path.dirname(
    ...     canonical.__file__)
    True
    """
    _cache = zope.thread.local()
    _default_config_section = os.environ.get('LAUNCHPAD_CONF', 'default')

    def setDefaultSection(self, section):
        """Set the name of the config file section returned by getConfig.
        
        This method is used by the test runner to switch on the test
        configuration. It may be used in the future to store the production
        configs in the one common file. It also sets the LAUNCHPAD_CONF
        environment variable so subprocesses keep the same default.
        """
        self._default_config_section = section
        os.environ['LAUNCHPAD_CONF'] = section

    def getConfig(self, section=None):
        """Return the ZConfig configuration"""

        if section is None:
            section = self._default_config_section

        try:
            return getattr(self._cache, section)
        except AttributeError:
            pass

        schemafile = os.path.join(os.path.dirname(__file__), 'schema.xml')
        configfile = os.path.join(
                os.path.dirname(__file__), os.pardir, os.pardir, os.pardir,
                'launchpad.conf'
                )
        schema = ZConfig.loadSchema(schemafile)
        root, handlers = ZConfig.loadConfig(schema, configfile)
        for branch in root.canonical:
            if branch.getSectionName() == section:
                setattr(self._cache, section, branch)
                self._magic_settings(branch)
                return branch
        raise KeyError, section

    def _magic_settings(self, config):
        """Modify the config, adding automatically generated settings"""

        # Root of the launchpad tree so code can stop jumping through hoops
        # with __file__
        config.root = os.path.abspath(os.path.join(
            os.path.dirname(__file__), os.pardir, os.pardir, os.pardir
            ))

    def __getattr__(self, name):
        return getattr(self.getConfig(), name)

    def default_section(self):
        return self._default_config_section
    default_section = property(default_section)

config = CanonicalConfig()

