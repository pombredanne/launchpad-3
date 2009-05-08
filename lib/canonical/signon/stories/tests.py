# Copyright 2004-2008 Canonical Ltd.  All rights reserved.

import os
import unittest

from openid.consumer.discover import OPENID_1_1_TYPE, OPENID_2_0_TYPE

from canonical.launchpad.testing.pages import PageTestSuite, setUpGlobs


here = os.path.dirname(os.path.realpath(__file__))


def test_suite():
    stories = sorted(
        dir for dir in os.listdir(here)
        if not dir.startswith('.') and os.path.isdir(os.path.join(here, dir)))

    suite = unittest.TestSuite()
    for storydir in stories:
        suite.addTest(PageTestSuite(storydir))

    # Add per-version page tests to the suite, once for each OpenID
    # version.
    pagetestsdir = os.path.join('openid', 'per-version')
    for PROTOCOL_URI in [OPENID_1_1_TYPE, OPENID_2_0_TYPE]:
        def setUp(test, PROTOCOL_URI=PROTOCOL_URI):
            setUpGlobs(test)
            test.globs['PROTOCOL_URI'] = PROTOCOL_URI
        suite.addTest(PageTestSuite(pagetestsdir, setUp=setUp))

    return suite
