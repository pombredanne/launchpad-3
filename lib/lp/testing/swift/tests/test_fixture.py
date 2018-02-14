# Copyright 2013-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Testing the mock Swift test fixture."""

__metaclass__ = type
__all__ = []

from datetime import datetime
from hashlib import md5

from requests.exceptions import ConnectionError
from swiftclient import client as swiftclient
from swiftclient.exceptions import ClientException
from testtools.matchers import (
    GreaterThan,
    LessThan,
    Not,
    )

from lp.services.config import config
from lp.testing import TestCase
from lp.testing.factory import ObjectFactory
from lp.testing.layers import BaseLayer
from lp.testing.swift import fakeswift
from lp.testing.swift.fixture import SwiftFixture


class TestSwiftFixture(TestCase):
    layer = BaseLayer

    def setUp(self):
        super(TestSwiftFixture, self).setUp()
        self.swift_fixture = SwiftFixture()
        self.useFixture(self.swift_fixture)
        self.factory = ObjectFactory()

    def makeSampleObject(self, client, contents, content_type=None):
        """Create a new container and a new sample object within it."""
        cname = self.factory.getUniqueString()
        oname = self.factory.getUniqueString()
        client.put_container(cname)
        client.put_object(cname, oname, contents, content_type=content_type)
        return cname, oname

    def test_get(self):
        client = self.swift_fixture.connect()
        size = 30
        headers, body = client.get_object("size", str(size))
        self.assertEqual("0" * size, body)
        self.assertEqual(str(size), headers["content-length"])
        self.assertEqual("text/plain", headers["content-type"])

    def test_get_404(self):
        client = self.swift_fixture.connect()
        cname = self.factory.getUniqueString()
        client.put_container(cname)
        exc = self.assertRaises(
            swiftclient.ClientException,
            client.get_object, cname, "nonexistent")
        self.assertEqual(404, exc.http_status)

    def test_get_403(self):
        client = self.swift_fixture.connect(key="bad key")
        exc = self.assertRaises(
            swiftclient.ClientException, client.get_container, "size")
        # swiftclient should possibly set exc.http_status here, but doesn't.
        self.assertEqual(
            'Authorization Failure. '
            'Authorization Failed: Forbidden (HTTP 403)',
            exc.message)

    def test_put(self):
        client = self.swift_fixture.connect()
        message = "Hello World!"
        cname, oname = self.makeSampleObject(client, message, "text/something")
        for x in range(1, 10):
            headers, body = client.get_object(cname, oname)
            self.assertEqual(message * x, body)
            self.assertEqual(str(len(message) * x), headers["content-length"])
            self.assertEqual("text/something", headers["content-type"])
            client.put_object(
                cname, oname, message * (x + 1), content_type="text/something")

    def test_get_container(self):
        # Basic container listing.
        start = datetime.utcnow().replace(microsecond=0)
        client = self.swift_fixture.connect()
        message = "42"
        cname, oname = self.makeSampleObject(client, message, "text/something")
        client.put_object(cname, oname + ".2", message)

        _, container = client.get_container(cname)
        self.assertEqual(2, len(container))
        obj = container[0]
        self.assertEqual(oname, obj["name"])
        self.assertEqual(len(message), obj["bytes"])
        self.assertEqual(md5(message).hexdigest(), obj["hash"])
        self.assertEqual("text/something", obj["content-type"])
        last_modified = datetime.strptime(
            obj["last_modified"], "%Y-%m-%dT%H:%M:%S.%f")  # ISO format
        self.assertThat(last_modified, Not(LessThan(start)))
        self.assertThat(last_modified, Not(GreaterThan(datetime.utcnow())))

    def test_get_container_marker(self):
        # Container listing supports the marker parameter.
        client = self.swift_fixture.connect()
        message = "Hello"
        cname, oname = self.makeSampleObject(client, message, "text/something")
        oname2 = oname + ".2"
        oname3 = oname + ".3"
        client.put_object(cname, oname2, message)
        client.put_object(cname, oname3, message)

        # List contents found after name == marker.
        _, container = client.get_container(cname, marker=oname)
        self.assertEqual(2, len(container))
        self.assertEqual(oname2, container[0]["name"])
        self.assertEqual(oname3, container[1]["name"])

    def test_get_container_end_marker(self):
        # Container listing supports the end_marker parameter.
        client = self.swift_fixture.connect()
        message = "Hello"
        cname, oname = self.makeSampleObject(client, message, "text/something")
        oname2 = oname + ".2"
        oname3 = oname + ".3"
        client.put_object(cname, oname2, message)
        client.put_object(cname, oname3, message)

        # List contents found before name == end_marker.
        _, container = client.get_container(cname, end_marker=oname3)
        self.assertEqual(2, len(container))
        self.assertEqual(oname, container[0]["name"])
        self.assertEqual(oname2, container[1]["name"])

    def test_get_container_limit(self):
        # Container listing supports the limit parameter.
        client = self.swift_fixture.connect()
        message = "Hello"
        cname, oname = self.makeSampleObject(client, message, "text/something")
        oname2 = oname + ".2"
        oname3 = oname + ".3"
        client.put_object(cname, oname2, message)
        client.put_object(cname, oname3, message)

        # Limit list to two objects.
        _, container = client.get_container(cname, limit=2)
        self.assertEqual(2, len(container))
        self.assertEqual(oname, container[0]["name"])
        self.assertEqual(oname2, container[1]["name"])

    def test_get_container_prefix(self):
        client = self.swift_fixture.connect()
        message = "Hello"
        cname, oname = self.makeSampleObject(client, message, "text/something")
        oname2 = "different"
        oname3 = oname + ".3"
        client.put_object(cname, oname2, message)
        client.put_object(cname, oname3, message)

        # List contents whose object names start with prefix.
        _, container = client.get_container(cname, prefix=oname)
        self.assertEqual(2, len(container))
        self.assertEqual(oname, container[0]["name"])
        self.assertEqual(oname3, container[1]["name"])

    def test_get_container_full_listing(self):
        client = self.swift_fixture.connect()
        message = "42"
        cname, oname = self.makeSampleObject(client, message, "text/something")

        _, container = client.get_container(cname, full_listing=True)
        self.assertEqual(1, len(container))

    def test_shutdown_and_startup(self):
        # This test demonstrates how the Swift client deals with a
        # flapping Swift server. In particular, that once a connection
        # has started failing it will continue failing so we need to
        # ensure that once we encounter a fail we open a fresh
        # connection. This is probably a property of our mock Swift
        # server rather than reality but the mock is a required target.
        size = 30

        # With no Swift server, a fresh connection fails with
        # a swiftclient.ClientException when it fails to
        # authenticate.
        self.swift_fixture.shutdown()
        client = self.swift_fixture.connect()
        self.assertRaises(
            swiftclient.ClientException,
            client.get_object, "size", str(size))

        # Things work fine when the Swift server is up.
        self.swift_fixture.startup()
        headers, body = client.get_object("size", str(size))
        self.assertEqual(body, "0" * size)

        # But if the Swift server goes away again, we end up with
        # different failures since the connection has already
        # authenticated.
        self.swift_fixture.shutdown()
        self.assertRaises(
            ConnectionError,
            client.get_object, "size", str(size))

        # And even if we bring it back up, existing connections
        # continue to fail
        self.swift_fixture.startup()
        self.assertRaises(
            ClientException,
            client.get_object, "size", str(size))

        # But fresh connections are fine.
        client = self.swift_fixture.connect()
        headers, body = client.get_object("size", str(size))
        self.assertEqual(body, "0" * size)

    def test_env(self):
        self.assertEqual(
            fakeswift.DEFAULT_USERNAME, config.librarian_server.os_username)
        self.assertEqual(
            fakeswift.DEFAULT_PASSWORD, config.librarian_server.os_password)
        self.assertEqual(
            'http://localhost:{0}/keystone/v2.0/'.format(
                self.swift_fixture.daemon_port),
            config.librarian_server.os_auth_url)
        self.assertEqual(
            fakeswift.DEFAULT_TENANT_NAME,
            config.librarian_server.os_tenant_name)
