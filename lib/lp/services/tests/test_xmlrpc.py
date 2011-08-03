# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the generic and/or shared xmlrpc code that Launchpad provides."""

__metaclass__ = type

import httplib

from canonical.testing.layers import BaseLayer
from lp.services.xmlrpc import (
    HTTP,
    Transport,
    )
from lp.testing import TestCase


class DummyConnectionClass:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __getattr__(self, name):
        return name


class TestTransport(TestCase):
    """Test code that allows xmlrpclib.ServerProxy to have a socket timeout"""

    layer = BaseLayer

    def test_default_initialization(self):
        transport = Transport()
        conn = httplib.HTTPConnection('localhost')
        self.assertEqual(conn.timeout, transport.timeout)

    def test_custom_initialization(self):
        transport = Transport(timeout=25)
        self.assertEqual(25, transport.timeout)

    def test_timeout_passed_to_connection(self):
        # The _connection_class is actually set on a parent class.  We verify
        # this, so we can just delete it from the class at the end.
        self.assertEqual(self, HTTP.__dict__.get('_connection_class', self))
        HTTP._connection_class = DummyConnectionClass
        try:
            transport = Transport(timeout=25)
            http = transport.make_connection('localhost')
            self.assertEqual(25, http._conn.kwargs['timeout'])
        finally:
            del HTTP.__dict__['_connection_class']
