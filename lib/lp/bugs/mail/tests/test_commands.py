# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from doctest import DocTestSuite

from lp.bugs.mail.commands import (
    AffectsEmailCommand,
    )
from lp.testing import TestCase


class AffectsEmailCommandTestCase(TestCase):

    def test__splitPath_with_slashes(self):
        self.assertEqual(
            ('foo', 'bar/baz'), AffectsEmailCommand._splitPath('foo/bar/baz'))

    def test__splitPath_no_slashes(self):
        self.assertEqual(
            ('foo', ''), AffectsEmailCommand._splitPath('foo'))

def test_suite():
    return DocTestSuite('lp.bugs.mail.commands')
