# Copyright 2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Testing the mock Swift test fixture."""

__metaclass__ = type
__all__ = []

from swiftclient import client as swiftclient

from lp.testing import TestCase
from lp.testing.layers import BaseLayer
from lp.testing.swift.fixture import SwiftFixture


class TestSwiftFixture(TestCase):
    layer = BaseLayer

    def test_get_works(self):
        with SwiftFixture() as fixture:
            client = fixture.connect()
            size = 30
            headers, body = client.get_object("size", str(size))
            self.assertEquals(body, "0" * size)
            self.assertEqual(str(size), headers["content-length"])
            self.assertEqual("text/plain", headers["content-type"])

    def test_get_fails(self):
        with SwiftFixture() as fixture:
            fixture.shutdown()
            client = fixture.connect()
            size = 30
            self.assertRaises(
                swiftclient.ClientException,
                client.get_object, "size", str(size))
