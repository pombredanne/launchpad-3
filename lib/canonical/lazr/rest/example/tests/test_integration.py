# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Test harness for LAZR doctests."""

__metaclass__ = type
__all__ = []

import os

from zope.app.publication.zopepublication import ZopePublication
from canonical.launchpad.testing.systemdocs import LayeredDocFileSuite

from zope.app.testing.functional import FunctionalTestSetup
from zope.configuration import xmlconfig
from canonical.lazr.testing.layers import MockRootFolder


def tearDown(test):
    """Run registered clean-up function."""
    FunctionalTestSetup()._init = False


def test_suite():
    """See `zope.testing.testrunner`."""
    zcmlcontext = xmlconfig.string("""
            <configure xmlns="http://namespaces.zope.org/zope">
              <include package="zope.app.component" file="meta.zcml"/>
              <include package="canonical.lazr.rest" />
              <include package="zope.traversing" />
              <include package="zope.publisher" />
              <include package="canonical.lazr.rest" file="meta.zcml" />
              <include package="canonical.lazr.rest.example" />
            </configure>""")
    fs = FunctionalTestSetup(
        config_file='lib/canonical/lazr/rest/ftesting.zcml')
    fs.setUp()
    if not fs.connection:
        fs.connection = fs.db.open()
    root = fs.connection.root()
    root[ZopePublication.root_name] = MockRootFolder()

    tests = sorted(
        [name
         for name in os.listdir(os.path.dirname(__file__))
         if name.endswith('.txt')])
    return LayeredDocFileSuite(
        stdout_logging=True, tearDown=tearDown, *tests)
