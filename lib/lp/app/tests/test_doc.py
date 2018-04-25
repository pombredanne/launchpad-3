# Copyright 2010-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
Run the doctests and pagetests.
"""

import os

from lp.services.features.testing import FeatureFixture
from lp.services.testing import build_test_suite
from lp.testing.layers import LaunchpadFunctionalLayer
from lp.testing.pages import (
    PageTestSuite,
    setUpGlobs,
    )
from lp.testing.systemdocs import (
    LayeredDocFileSuite,
    setUp,
    tearDown,
    )


here = os.path.dirname(os.path.realpath(__file__))
bing_flag = FeatureFixture({'sitesearch.engine.name': 'bing'})
google_flag = FeatureFixture({'sitesearch.engine.name': 'google'})


def setUp_bing(test):
    setUpGlobs(test)
    bing_flag.setUp()


def setUp_google(test):
    setUpGlobs(test)
    google_flag.setUp()


def tearDown_bing(test):
    bing_flag.cleanUp()
    tearDown(test)


def tearDown_google(test):
    google_flag.cleanUp()
    tearDown(test)


special = {
    'tales.txt': LayeredDocFileSuite(
        '../doc/tales.txt',
        setUp=setUp, tearDown=tearDown,
        layer=LaunchpadFunctionalLayer,
        ),
    'menus.txt': LayeredDocFileSuite(
        '../doc/menus.txt', layer=None,
        ),
    'stories/launchpad-search(Bing)': PageTestSuite(
        '../stories/launchpad-search/',
        id_extensions=['site-search.txt(Bing)'],
        setUp=setUp_bing, tearDown=tearDown_bing,
        ),
    'stories/launchpad-search(Google)': PageTestSuite(
        '../stories/launchpad-search/',
        id_extensions=['site-search.txt(Google)'],
        setUp=setUp_google, tearDown=tearDown_google,
        ),
    # Run these doctests again with the default search engine.
    '../stories/launchpad-search': PageTestSuite(
        '../stories/launchpad-search/',
        setUp=setUpGlobs, tearDown=tearDown,
        ),
    }


def test_suite():
    return build_test_suite(here, special)
