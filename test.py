#!/usr/bin/env python2.3
##############################################################################
#
# Copyright (c) 2004 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Test script

$Id: test.py 25177 2004-06-02 13:17:31Z jim $
"""
import sys, os

here = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(here, 'lib'))

# Set PYTHONPATH environment variable for spawned processes
os.environ['PYTHONPATH'] = ':'.join(sys.path)

# This is a hack to use canonical.difflib instead of standard difflib
# so we can easily test it. Comment out and commit to rocketfuel if
# it causes grief -- StuartBishop 20041130
# Turned off - we need more context or linenumbers. eg. I'm being told I
# have an unexpected line, but no way to tell where.
def monkey_patch_doctest():
    import canonical.difflib
    sys.modules['difflib'] = canonical.difflib
    import difflib
    assert hasattr(difflib.Differ, 'fancy_compare'), \
            'Failed to monkey patch difflib'
    import zope.testing.doctest
    import canonical.doctest
    zope.testing.doctest.OutputChecker = canonical.doctest.OutputChecker
# monkey_patch_doctest()

# This is a terrible hack to divorce the FunctionalTestSetup from
# its assumptions about the ZODB.
from zope.app.tests.functional import FunctionalTestSetup
FunctionalTestSetup.__init__ = lambda *x: None

import zope.app.tests.test

if __name__ == '__main__':
    zope.app.tests.test.process_args()
