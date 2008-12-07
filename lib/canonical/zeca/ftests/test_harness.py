# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.testing import doctest

from canonical.launchpad.testing.systemdocs import default_optionflags

def test_suite():
    return doctest.DocTestSuite(
        'canonical.zeca.ftests.harness', optionflags=default_optionflags)

