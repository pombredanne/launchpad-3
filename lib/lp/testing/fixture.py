# Copyright 2009, 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Launchpad test fixtures that have no better home."""

__metaclass__ = type
__all__ = [
    'RabbitServer',
    'ZopeAdapterFixture',
    'ZopeEventHandlerFixture',
    'ZopeViewReplacementFixture',
    ]

from ConfigParser import SafeConfigParser
import os.path
from textwrap import dedent

from fixtures import (
    EnvironmentVariableFixture,
    Fixture,
    )
import pgbouncer.fixture
import rabbitfixture.server
from zope.component import (
    getGlobalSiteManager,
    provideHandler,
    )
from zope.interface import Interface
from zope.publisher.interfaces.browser import IDefaultBrowserLayer
from zope.security.checker import (
    defineChecker,
    getCheckerForInstancesOf,
    undefineChecker,
    )

from canonical.config import config


class RabbitServer(rabbitfixture.server.RabbitServer):
    """A RabbitMQ server fixture with Launchpad-specific config.

    :ivar service_config: A snippet of .ini that describes the `rabbitmq`
        configuration.
    """

    def setUp(self):
        super(RabbitServer, self).setUp()
        self.config.service_config = dedent("""\
            [rabbitmq]
            host: localhost:%d
            userid: guest
            password: guest
            virtual_host: /
            """ % self.config.port)


class PGBouncerFixture(pgbouncer.fixture.PGBouncerFixture):
    """Inserts a controllable pgbouncer instance in front of PostgreSQL.

    The pgbouncer proxy can be shutdown and restarted at will, simulating
    database outages as fastdowntime deployments.
    """

    def __init__(self):
        super(PGBouncerFixture, self).__init__()

        # Known databases
        from canonical.testing.layers import DatabaseLayer
        dbnames = [
            DatabaseLayer._db_fixture.dbname,
            DatabaseLayer._db_template_fixture.dbname,
            'session_ftest',
            'launchpad_empty',
            ]
        for dbname in dbnames:
            self.databases[dbname] = 'dbname=%s port=5432 host=localhost' % (
                dbname,)

        # Known users, pulled from security.cfg
        security_cfg_path = os.path.join(
            config.root, 'database', 'schema', 'security.cfg')
        security_cfg_config = SafeConfigParser({})
        security_cfg_config.read([security_cfg_path])
        for section_name in security_cfg_config.sections():
            self.users[section_name] = 'trusted'
        self.users[os.environ['USER']] = 'trusted'

    def setUp(self):
        super(PGBouncerFixture, self).setUp()

        # reconnect_store cleanup added first so it is run last, after
        # the environment variables have been reset.
        from canonical.testing.layers import reconnect_stores
        self.addCleanup(reconnect_stores)

        # Abuse the PGPORT environment variable to get things connecting
        # via pgbouncer. Otherwise, we would need to temporarily
        # overwrite the database connection strings in the config.
        self.useFixture(EnvironmentVariableFixture('PGPORT', str(self.port)))

        # Reset database connections so they go through pgbouncer.
        reconnect_stores()


class ZopeAdapterFixture(Fixture):
    """A fixture to register and unregister an adapter."""

    def __init__(self, *args, **kwargs):
        self._args, self._kwargs = args, kwargs

    def setUp(self):
        super(ZopeAdapterFixture, self).setUp()
        site_manager = getGlobalSiteManager()
        site_manager.registerAdapter(
            *self._args, **self._kwargs)
        self.addCleanup(
            site_manager.unregisterAdapter,
            *self._args, **self._kwargs)


class ZopeEventHandlerFixture(Fixture):
    """A fixture that provides and then unprovides a Zope event handler."""

    def __init__(self, handler):
        super(ZopeEventHandlerFixture, self).__init__()
        self._handler = handler

    def setUp(self):
        super(ZopeEventHandlerFixture, self).setUp()
        gsm = getGlobalSiteManager()
        provideHandler(self._handler)
        self.addCleanup(gsm.unregisterHandler, self._handler)


class ZopeViewReplacementFixture(Fixture):
    """A fixture that allows you to temporarily replace one view with another.

    This will not work with the AppServerLayer.
    """

    def __init__(self, name, context_interface,
                 request_interface=IDefaultBrowserLayer,
                 replacement=None):
        super(ZopeViewReplacementFixture, self).__init__()
        self.name = name
        self.context_interface = context_interface
        self.request_interface = request_interface
        self.gsm = getGlobalSiteManager()
        # It can be convenient--bordering on necessary--to use this original
        # class as a base for the replacement.
        self.original = self.gsm.adapters.registered(
            (context_interface, request_interface), Interface, name)
        self.checker = getCheckerForInstancesOf(self.original)
        if self.original is None:
            # The adapter registry does not provide good methods to introspect
            # it. If it did, we might try harder here.
            raise ValueError(
                'No existing view to replace.  Wrong request interface?  '
                'Try a layer.')
        self.replacement = replacement

    def setUp(self):
        super(ZopeViewReplacementFixture, self).setUp()
        if self.replacement is None:
            raise ValueError('replacement is not set')
        self.gsm.adapters.register(
            (self.context_interface, self.request_interface), Interface,
             self.name, self.replacement)
        # The same checker should be sufficient.  If it ever isn't, we
        # can add more flexibility then.
        defineChecker(self.replacement, self.checker)

    def tearDown(self):
        super(ZopeViewReplacementFixture, self).tearDown()
        undefineChecker(self.replacement)
        self.gsm.adapters.register(
            (self.context_interface, self.request_interface), Interface,
             self.name, self.original)
