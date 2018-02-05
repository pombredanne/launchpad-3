# Copyright 2010-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unit tests for TestSourcePackageReleaseFiles."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TestSourcePackageReleaseView',
    ]

from lp.testing import TestCaseWithFactory
from lp.testing.factory import remove_security_proxy_and_shout_at_engineer
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.views import create_initialized_view


class TestSourcePackageReleaseView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestSourcePackageReleaseView, self).setUp()
        self.source_package_release = self.factory.makeSourcePackageRelease()

    def test_highlighted_copyright_is_None(self):
        expected = ''
        remove_security_proxy_and_shout_at_engineer(
            self.source_package_release).copyright = None
        view = create_initialized_view(
            self.source_package_release, '+copyright')
        self.assertEqual(expected, view.highlighted_copyright)

    def test_highlighted_copyright_no_matches(self):
        expected = 'nothing to see and/or do.'
        remove_security_proxy_and_shout_at_engineer(
            self.source_package_release).copyright = expected
        view = create_initialized_view(
            self.source_package_release, '+copyright')
        self.assertEqual(expected, view.highlighted_copyright)

    def test_highlighted_copyright_match_url(self):
        remove_security_proxy_and_shout_at_engineer(
            self.source_package_release).copyright = (
            'Downloaded from https://upstream.dom/fnord/no/ and')
        expected = (
            'Downloaded from '
            '<span class="highlight">https://upstream.dom/fnord/no/</span> '
            'and')
        view = create_initialized_view(
            self.source_package_release, '+copyright')
        self.assertEqual(expected, view.highlighted_copyright)

    def test_highlighted_copyright_match_path(self):
        remove_security_proxy_and_shout_at_engineer(
            self.source_package_release).copyright = (
            'See /usr/share/common-licenses/GPL')
        expected = (
            'See '
            '<span class="highlight">/usr/share/common-licenses/GPL</span>')
        view = create_initialized_view(
            self.source_package_release, '+copyright')
        self.assertEqual(expected, view.highlighted_copyright)

    def test_highlighted_copyright_match_multiple(self):
        remove_security_proxy_and_shout_at_engineer(
            self.source_package_release).copyright = (
            'See /usr/share/common-licenses/GPL or https://osi.org/mit')
        expected = (
            'See '
            '<span class="highlight">/usr/share/common-licenses/GPL</span> '
             'or <span class="highlight">https://osi.org/mit</span>')
        view = create_initialized_view(
            self.source_package_release, '+copyright')
        self.assertEqual(expected, view.highlighted_copyright)
