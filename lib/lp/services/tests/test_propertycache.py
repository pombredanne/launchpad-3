# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for lp.services.propertycache."""

__metaclass__ = type

from canonical.testing import LaunchpadZopelessLayer
from lp.services import propertycache


def test_suite():
    from doctest import DocTestSuite, ELLIPSIS
    suite = DocTestSuite(propertycache, optionflags=ELLIPSIS)
    suite.layer = LaunchpadZopelessLayer
    return suite
