# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'TestOpenIDRootUrlData',
    'TestOpenIDNavigation',
    ]


from zope.interface import implements

from canonical.launchpad.webapp.interfaces import ICanonicalUrlData
from canonical.launchpad.webapp import Navigation

from canonical.launchpad.layers import TestOpenIDLayer
from canonical.launchpad.interfaces.launchpad import (
    ITestOpenIDApplication)


class TestOpenIDNavigation(Navigation):
    usedfor = ITestOpenIDApplication
    newlayer = TestOpenIDLayer


class TestOpenIDRootUrlData:
    """`ICanonicalUrlData` for the test OpenID provider."""

    implements(ICanonicalUrlData)

    path = ''
    inside = None
    rootsite = 'testopenid'

    def __init__(self, context):
        self.context = context
