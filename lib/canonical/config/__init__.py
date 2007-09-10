# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
'''
Configuration information pulled from launchpad.conf.

The configuration section used is specified using the LPCONFIG
environment variable, and defaults to 'default'
'''

__metaclass__ = type

import os
import logging
from urlparse import urlparse, urlunparse

import zope.thread
import ZConfig

# LPCONFIG specifies the config to use, which corresponds to a subdirectory
# of configs. LPCONFIG_SECTION specifies the <canonical> section inside that
# config's launchpad.conf to use. LPCONFIG_SECTION is really only used by
# the test suite to select the testrunner specific section.
CONFIG_ENVIRONMENT_VARIABLE = 'LPCONFIG'
SECTION_ENVIRONMENT_VARIABLE = 'LPCONFIG_SECTION'

DEFAULT_SECTION = 'default'
DEFAULT_CONFIG = 'default'

class CanonicalConfig(object):
    """
    Singleton configuration, accessed via the `config` module global.

    Cached copies are kept in thread locals ensuring the configuration
    is thread safe (not that this will be a problem if we stick with
    simple configuration).

    >>> from canonical.config import config
    >>> config.dbhost
    'localhost'
    >>> config.launchpad.db_statement_timeout is None
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
    >>> config.name == os.environ.get('LPCONFIG', DEFAULT_SECTION)
    True
    """
    _cache = zope.thread.local()
    _default_config_section = os.environ.get(
            SECTION_ENVIRONMENT_VARIABLE, DEFAULT_SECTION
            )

    def setDefaultSection(self, section):
        """Set the name of the config file section returned by getConfig.

        This method is used by the test runner to switch on the test
        configuration. It may be used in the future to store the production
        configs in the one common file. It also sets the LPCONFIG_SECTION
        environment variable so subprocesses keep the same default.
        """
        self._default_config_section = section
        os.environ[SECTION_ENVIRONMENT_VARIABLE] = section

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
                'configs',os.environ.get(
                    CONFIG_ENVIRONMENT_VARIABLE, DEFAULT_CONFIG),
                'launchpad.conf'
                )
        schema = ZConfig.loadSchema(schemafile)
        root, handlers = ZConfig.loadConfig(schema, configfile)
        for branch in root.canonical:
            if branch.getSectionName() == section:
                setattr(self._cache, section, branch)
                self._magic_settings(branch, root)
                return branch
        raise KeyError, section

    def _magic_settings(self, config, root_options):
        """Modify the config, adding automatically generated settings"""

        # Root of the launchpad tree so code can stop jumping through hoops
        # with __file__
        config.root = os.path.abspath(os.path.join(
            os.path.dirname(__file__), os.pardir, os.pardir, os.pardir
            ))

        # Name of the current configuration, as per LPCONFIG environment
        # variable
        config.name = os.environ.get(
                CONFIG_ENVIRONMENT_VARIABLE, DEFAULT_CONFIG)

        # Devmode from the zope.app.server.main config, copied here for
        # ease of access.
        config.devmode = root_options.devmode

    def __getattr__(self, name):
        return getattr(self.getConfig(), name)

    def default_section(self):
        return self._default_config_section
    default_section = property(default_section)

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
        'soft_request_timeout', 'randomise_select_results'])
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
        return [overlay, config]

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
