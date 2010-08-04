# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the helpers in `lp.testing.publication`."""

__metaclass__ = type

from zope.component import getSiteManager
from zope.interface import Interface
from zope.publisher.interfaces.browser import IDefaultBrowserLayer

from canonical.testing import DatabaseFunctionalLayer
from lp.testing import ANONYMOUS, login, TestCaseWithFactory
from lp.testing.publication import test_traverse
from canonical.launchpad.interfaces.launchpad import ILaunchpadRoot
from lp.registry.interfaces.product import IProduct

class TestTestTraverse(TestCaseWithFactory):
    # Tests for `test_traverse`

    layer = DatabaseFunctionalLayer

    def registerViewClass(self, v):
        name = '+' + self.factory.getUniqueString()
        getSiteManager().registerAdapter(
            v, (IProduct, IDefaultBrowserLayer), Interface, name)
        return 'https://launchpad.dev/firefox/' + name

    def test_traverse_simple(self):
        login(ANONYMOUS)
        o, v, r = test_traverse('https://launchpad.dev/firefox/+index')
        print (o, v, r)

    def test_custom_view_class(self):
        login(ANONYMOUS)
        def v(*args):
            print 'v', args
        o, v, r = test_traverse(self.registerViewClass(v))
        print (o, v, r)
        
