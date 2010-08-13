# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test for virtual host setup."""

__metaclass__ = type

from doctest import DocTestSuite, NORMALIZE_WHITESPACE, ELLIPSIS

def test_suite():
    suite = DocTestSuite(
            'canonical.launchpad.webapp.vhosts',
            optionflags=NORMALIZE_WHITESPACE | ELLIPSIS
            )
    return suite

