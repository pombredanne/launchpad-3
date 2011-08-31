# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for lp.testing.fixture."""

__metaclass__ = type

from textwrap import dedent

from fixtures import EnvironmentVariableFixture
import psycopg2
from storm.exceptions import DisconnectionError
from zope.component import (
    adapts,
    queryAdapter,
    )
from zope.interface import (
    implements,
    Interface,
    )

from canonical.config import dbconfig
from canonical.launchpad.interfaces.lpstorm import IMasterStore
from canonical.testing.layers import (
    BaseLayer,
    DatabaseLayer,
    LaunchpadZopelessLayer,
    )
from lp.registry.model.person import Person
from lp.testing import TestCase
from lp.testing.fixture import (
    PGBouncerFixture,
    RabbitServer,
    ZopeAdapterFixture,
    )


class TestRabbitServer(TestCase):

    layer = BaseLayer

    def test_service_config(self):
        # Rabbit needs to fully isolate itself: an existing per user
        # .erlange.cookie has to be ignored, and ditto bogus HOME if other
        # tests fail to cleanup.
        self.useFixture(EnvironmentVariableFixture('HOME', '/nonsense/value'))

        # RabbitServer pokes some .ini configuration into its config.
        with RabbitServer() as fixture:
            expected = dedent("""\
                [rabbitmq]
                host: localhost:%d
                userid: guest
                password: guest
                virtual_host: /
                """ % fixture.config.port)
            self.assertEqual(expected, fixture.config.service_config)


class IFoo(Interface):
    pass


class IBar(Interface):
    pass


class Foo:
    implements(IFoo)


class Bar:
    implements(IBar)


class FooToBar:

    adapts(IFoo)
    implements(IBar)

    def __init__(self, foo):
        self.foo = foo


class TestZopeAdapterFixture(TestCase):

    layer = BaseLayer

    def test_register_and_unregister(self):
        # Entering ZopeAdapterFixture's context registers the given adapter,
        # and exiting the context unregisters the adapter again.
        context = Foo()
        # No adapter from Foo to Bar is registered.
        self.assertIs(None, queryAdapter(context, IBar))
        with ZopeAdapterFixture(FooToBar):
            # Now there is an adapter from Foo to Bar.
            adapter = queryAdapter(context, IBar)
            self.assertIsNot(None, adapter)
            self.assertIsInstance(adapter, FooToBar)
        # The adapter is no longer registered.
        self.assertIs(None, queryAdapter(context, IBar))


class TestPGBouncerFixtureWithCA(TestCase):
    """PGBouncerFixture reconnect tests for Component Architecture layers.

    Registered Storm Stores should be reconnected through pgbouncer.
    """
    layer = LaunchpadZopelessLayer

    def is_connected(self):
        # First rollback any existing transaction to ensure we attempt
        # to reconnect. We currently rollback the store explicitely
        # rather than call transaction.abort() due to Bug #819282.
        store = IMasterStore(Person)
        store.rollback()

        try:
            store.find(Person).first()
            return True
        except DisconnectionError:
            return False

    def test_stop_and_start(self):
        # Database is working.
        assert self.is_connected()

        # And database with the fixture is working too.
        pgbouncer = PGBouncerFixture()
        with PGBouncerFixture() as pgbouncer:
            assert self.is_connected()

            # pgbouncer is transparant. To confirm we are connecting via
            # pgbouncer, we need to shut it down and confirm our
            # connections are dropped.
            pgbouncer.stop()
            assert not self.is_connected()

            # If we restart it, things should be back to normal.
            pgbouncer.start()
            assert self.is_connected()

        # Database is still working.
        assert self.is_connected()

    def test_stop_no_start(self):
        # Database is working.
        assert self.is_connected()

        # And database with the fixture is working too.
        with PGBouncerFixture() as pgbouncer:
            assert self.is_connected()

            # pgbouncer is transparant. To confirm we are connecting via
            # pgbouncer, we need to shut it down and confirm our
            # connections are dropped.
            pgbouncer.stop()
            assert not self.is_connected()

        # Database is working again.
        assert self.is_connected()


class TestPGBouncerFixtureWithoutCA(TestCase):
    """PGBouncerFixture tests for non-Component Architecture layers."""
    layer = DatabaseLayer

    def is_db_available(self):
        # Direct connection to the DB.
        con_str = dbconfig.rw_main_master + ' user=launchpad_main'
        try:
            con = psycopg2.connect(con_str)
            cur = con.cursor()
            cur.execute("SELECT id FROM Person LIMIT 1")
            con.close()
            return True
        except psycopg2.OperationalError:
            return False

    def test_install_fixture(self):
        self.assert_(self.is_db_available())

        with PGBouncerFixture() as pgbouncer:
            self.assert_(self.is_db_available())

            pgbouncer.stop()
            self.assert_(not self.is_db_available())

        # This confirms that we are again connecting directly to the
        # database, as the pgbouncer process was shutdown.
        self.assert_(self.is_db_available())

    def test_install_fixture_with_restart(self):
        self.assert_(self.is_db_available())

        with PGBouncerFixture() as pgbouncer:
            self.assert_(self.is_db_available())

            pgbouncer.stop()
            self.assert_(not self.is_db_available())

            pgbouncer.start()
            self.assert_(self.is_db_available())

        # Note that because pgbouncer was left running, we can't confirm
        # that we are now connecting directly to the database.
        self.assert_(self.is_db_available())
