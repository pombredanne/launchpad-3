# Copyright 2004-2008 Canonical Ltd.  All rights reserved.
'''
Configuration information pulled from launchpad.conf.

The configuration section used is specified using the LPCONFIG
environment variable, and defaults to 'development'
'''

__metaclass__ = type


import os
import logging
import sys
from urlparse import urlparse, urlunparse

import ZConfig

from canonical.lazr.config import ImplicitTypeSchema
from canonical.lazr.interfaces.config import ConfigErrors


# LPCONFIG specifies the config to use, which corresponds to a subdirectory
# of configs.
LPCONFIG = 'LPCONFIG'
DEFAULT_CONFIG = 'development'


class CanonicalConfig:
    """
    Singleton configuration, accessed via the `config` module global.

    Cached copies are kept in thread locals ensuring the configuration
    is thread safe (not that this will be a problem if we stick with
    simple configuration).
    """
    _config = None
    _instance_name = os.environ.get(LPCONFIG, DEFAULT_CONFIG)
    _process_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]

    @property
    def instance_name(self):
        """Return the config's instance name.

        This normally corresponds to the LPCONFIG environment
        variable. It is also the name of the directory the conf file is
        loaded from.
        """
        return self._instance_name

    def setInstance(self, instance_name):
        """Set the instance name where the conf files are stored.

        This method is used to set the instance_name, which is the
        directory where the conf file is stored. The test runner
        uses this to switch on the test configuration. This
        method also sets the LPCONFIG environment
        variable so subprocesses keep the same default.
        """
        self._instance_name = instance_name
        os.environ[LPCONFIG] = instance_name

    @property
    def process_name(self):
        """Return or set the current process's name to select a conf.

        CanonicalConfig loads the conf file named for the process. When
        the conf file does not exist, it loads launchpad-lazr.conf instead.
        """
        return self._process_name

    def setProcess(self, process_name):
        """Set the name of the process to select a conf file.

        This method is used to set the process_name is if should be
        different from the name obtained from sys.argv[0]. CanonicalConfig
        will try to load <process_name>-lazr.conf if it exists. Otherwise,
        it will load launchpad-lazr.conf.
        """
        self._process_name = process_name

    def _getConfig(self):
        """Get the schema and config for this environment.

        The config is will be loaded only when there is not a config.
        Repeated calls to this method will not cause the config to reload.
        """
        if self._config is not None:
            return

        here = os.path.dirname(__file__)
        schema_file = os.path.join(here, 'schema-lazr.conf')
        config_dir = os.path.join(
            here, os.pardir, os.pardir, os.pardir,
            'configs', self.instance_name)
        config_file = os.path.join(
            config_dir, '%s-lazr.conf' % self.process_name)
        if not os.path.isfile(config_file):
            config_file = os.path.join(config_dir, 'launchpad-lazr.conf')
        schema = ImplicitTypeSchema(schema_file)
        self._config = schema.load(config_file)
        try:
            self._config.validate()
        except ConfigErrors, error:
            message = '\n'.join([str(e) for e in error.errors])
            raise ConfigErrors(message)
        self._setZConfig(here, config_dir)

    def _setZConfig(self, here, config_dir):
        """Modify the config, adding automatically generated settings"""
        # Root of the launchpad tree so code can stop jumping through hoops
        # with __file__
        config.root = os.path.abspath(os.path.join(
            here, os.pardir, os.pardir, os.pardir))

        schemafile = os.path.join(
            config.root, 'lib/zope/app/server/schema.xml')
        configfile = os.path.join(config_dir, 'launchpad.conf')
        schema = ZConfig.loadSchema(schemafile)
        root_options, handlers = ZConfig.loadConfig(schema, configfile)

        # Devmode from the zope.app.server.main config, copied here for
        # ease of access.
        config.devmode = root_options.devmode

        # The defined servers.
        config.servers = root_options.servers

        # The number of configured threads.
        config.threads = root_options.threads

    def __getattr__(self, name):
        self._getConfig()
        return getattr(self._config, name)

    def __contains__(self, key):
        self._getConfig()
        return key in self._config

    def __getitem__(self, key):
        self._getConfig()
        return self._config[key]


config = CanonicalConfig()


def url(value):
    '''ZConfig validator for urls

    We enforce the use of protocol.

    >>> url('http://localhost:8086')
    'http://localhost:8086'
    >>> url('im-a-file-but-not-allowed')
    Traceback (most recent call last):
        [...]
    ValueError: No protocol in URL
    '''
    bits = urlparse(value)
    if not bits[0]:
        raise ValueError('No protocol in URL')
    value = urlunparse(bits)
    return value

def urlbase(value):
    """ZConfig validator for url bases

    url bases are valid urls that can be appended to using urlparse.urljoin.

    url bases always end with '/'

    >>> urlbase('http://localhost:8086')
    'http://localhost:8086/'
    >>> urlbase('http://localhost:8086/')
    'http://localhost:8086/'

    URL fragments, queries and parameters are not allowed

    >>> urlbase('http://localhost:8086/#foo')
    Traceback (most recent call last):
        [...]
    ValueError: URL fragments not allowed
    >>> urlbase('http://localhost:8086/?foo')
    Traceback (most recent call last):
        [...]
    ValueError: URL query not allowed
    >>> urlbase('http://localhost:8086/;blah=64')
    Traceback (most recent call last):
        [...]
    ValueError: URL parameters not allowed

    We insist on the protocol being specified, to avoid dealing with defaults
    >>> urlbase('foo')
    Traceback (most recent call last):
        [...]
    ValueError: No protocol in URL

    File URLs specify paths to directories

    >>> urlbase('file://bork/bork/bork')
    'file://bork/bork/bork/'
    """
    value = url(value)
    scheme, location, path, parameters, query, fragment = urlparse(value)
    if parameters:
        raise ValueError, 'URL parameters not allowed'
    if query:
        raise ValueError, 'URL query not allowed'
    if fragment:
        raise ValueError, 'URL fragments not allowed'
    if not value.endswith('/'):
        value = value + '/'
    return value


def commalist(value):
    """ZConfig validator for a comma seperated list"""
    return [v.strip() for v in value.split(',')]


def loglevel(value):
    """ZConfig validator for log levels.

    Input is a string ('info','debug','warning','error','fatal' etc.
    as per logging module), and output is the integer value.

    >>> import logging
    >>> loglevel("info") == logging.INFO
    True
    >>> loglevel("FATAL") == logging.FATAL
    True
    >>> loglevel("foo")
    Traceback (most recent call last):
    ...
    ValueError: ...
    """
    value = value.upper().strip()
    if value == 'DEBUG':
        return logging.DEBUG
    elif value == 'INFO':
        return logging.INFO
    elif value == 'WARNING' or value == 'WARN':
        return logging.WARNING
    elif value == 'ERROR':
        return logging.ERROR
    elif value == 'FATAL':
        return logging.FATAL
    else:
        raise ValueError(
                "Invalid log level %s. "
                "Should be DEBUG, CRITICAL, ERROR, FATAL, INFO, WARNING "
                "as per logging module." % value
                )


class DatabaseConfig:
    """A class to provide the Launchpad database configuration.

    The dbconfig option overlays the database configurations of a
    chosen config section over the base section:

        >>> from canonical.config import config, dbconfig
        >>> print config.dbhost
        localhost
        >>> print config.dbuser
        Traceback (most recent call last):
          ...
        AttributeError: ...
        >>> print config.launchpad.dbhost
        None
        >>> print config.launchpad.dbuser
        launchpad
        >>> print config.librarian.dbuser
        librarian

        >>> dbconfig.setConfigSection('librarian')
        >>> print dbconfig.dbhost
        localhost
        >>> print dbconfig.dbuser
        librarian

        >>> dbconfig.setConfigSection('launchpad')
        >>> print dbconfig.dbhost
        localhost
        >>> print dbconfig.dbuser
        launchpad

    Some values are required to have a value, such as dbuser.  So we
    get an exception if they are not set:

        >>> config.launchpad.dbuser = None
        >>> print dbconfig.dbuser
        Traceback (most recent call last):
          ...
        ValueError: dbuser must be set
        >>> config.launchpad.dbuser = 'launchpad'
    """
    _config_section = None
    _db_config_attrs = frozenset([
        'dbuser', 'dbhost', 'dbname', 'db_statement_timeout',
        'db_statement_timeout_precision', 'isolation_level',
        'randomise_select_results', 'soft_request_timeout'])
    _db_config_required_attrs = frozenset(['dbuser', 'dbname'])

    def setConfigSection(self, section_name):
        self._config_section = section_name

    def _getConfigSections(self):
        """Returns a list of sections to search for database configuration.

        The first section in the list has highest priority.
        """
        if self._config_section is None:
            return [config.database]
        overlay = config
        for part in self._config_section.split('.'):
            overlay = getattr(overlay, part)
        return [overlay, config.database]

    def __getattr__(self, name):
        sections = self._getConfigSections()
        if name not in self._db_config_attrs:
            raise AttributeError(name)
        value = None
        for section in sections:
            value = getattr(section, name, None)
            if value is not None:
                break
        # Some values must be provided by the config
        if value is None and name in self._db_config_required_attrs:
            raise ValueError('%s must be set' % name)
        return value


dbconfig = DatabaseConfig()
dbconfig.setConfigSection('launchpad')
