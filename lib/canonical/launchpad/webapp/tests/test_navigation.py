# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from zope.component import ComponentLookupError, getMultiAdapter
from zope.configuration import xmlconfig
from zope.interface import implements, Interface
from zope.publisher.interfaces.browser import (
    IBrowserPublisher, IDefaultBrowserLayer)
from zope.testing.cleanup import cleanUp

from canonical.launchpad.webapp import Navigation

from lp.testing import TestCase


class TestNavigationDirective(TestCase):

    def test_default_layer(self):
        # By default all navigation classes are registered for
        # IDefaultBrowserLayer.
        directive = """ 
            <browser:navigation
                module="%(this)s" classes="ThingNavigation"/>
            """ % dict(this=this)
        xmlconfig.string(zcml_configure % directive)
        navigation = getMultiAdapter(
            (Thing(), DefaultBrowserLayer()), IBrowserPublisher, name='')
        self.assertIsInstance(navigation, ThingNavigation)

    def test_specific_layer(self):
        # If we specify a layer when registering a navigation class, it will
        # only be available on that layer.
        directive = """
            <browser:navigation
                module="%(this)s" classes="ThingNavigation"
                layer="%(this)s.IOtherLayer" />
            """ % dict(this=this)
        xmlconfig.string(zcml_configure % directive)
        self.assertRaises(
            ComponentLookupError,
            getMultiAdapter,
            (Thing(), DefaultBrowserLayer()), IBrowserPublisher, name='')

        navigation = getMultiAdapter(
            (Thing(), OtherLayer()), IBrowserPublisher, name='')
        self.assertIsInstance(navigation, ThingNavigation)

    def tearDown(self):
        TestCase.tearDown(self)
        cleanUp()


class DefaultBrowserLayer:
    implements(IDefaultBrowserLayer)


class IThing(Interface):
    pass


class Thing(object):
    implements(IThing)


class ThingNavigation(Navigation):
    usedfor = IThing


class IOtherLayer(Interface):
    pass


class OtherLayer:
    implements(IOtherLayer)


this = "canonical.launchpad.webapp.tests.test_navigation"
zcml_configure = """
    <configure xmlns:browser="http://namespaces.zope.org/browser">
      <include package="canonical.launchpad.webapp" file="meta.zcml" />
      %s
    </configure>
    """
