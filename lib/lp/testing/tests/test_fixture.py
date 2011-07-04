# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for lp.testing.fixture."""

__metaclass__ = type

from zope.component import (
    adapts,
    queryAdapter,
    )
from zope.interface import (
    implements,
    Interface,
    )

from canonical.testing.layers import BaseLayer
from lp.testing import TestCase
from lp.testing.fixture import ZopeAdapterFixture


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
        context = Foo()
        # No adapter from Foo to Bar is registered.
        self.assertIs(None, queryAdapter(context, IBar))
        with ZopeAdapterFixture(FooToBar):
            # Now there is an adapter from Foo to Bar.
            adapter = queryAdapter(context, IBar)
            self.assertIsNot(None, adapter)
            self.assertIsInstance(adapter, FooToBar)
        # Again, it's no longer registered.
        self.assertIs(None, queryAdapter(context, IBar))
