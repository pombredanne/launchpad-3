# Copyright 2009-2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from lp.soyuz.adapters.buildarch import (
    determine_architectures_to_build,
    DpkgArchitectureCache,
    )
from lp.testing import TestCase


class TestDpkgArchitectureCache(TestCase):

    def test_multiple(self):
        self.assertContentEqual(
            ['amd64', 'armhf'],
            DpkgArchitectureCache().findAllMatches(
                ['amd64', 'i386', 'armhf'], ['amd64', 'armhf']))

    def test_any(self):
        self.assertContentEqual(
            ['amd64', 'i386', 'kfreebsd-amd64'],
            DpkgArchitectureCache().findAllMatches(
                ['amd64', 'i386', 'kfreebsd-amd64'], ['any']))

    def test_all(self):
        self.assertContentEqual(
            [],
            DpkgArchitectureCache().findAllMatches(
                ['amd64', 'i386', 'kfreebsd-amd64'], ['all']))

    def test_partial_wildcards(self):
        self.assertContentEqual(
            ['amd64', 'i386', 'kfreebsd-amd64'],
            DpkgArchitectureCache().findAllMatches(
                ['amd64', 'i386', 'kfreebsd-amd64', 'kfreebsd-i386'],
                ['linux-any', 'any-amd64']))


class TestDetermineArchitecturesToBuild(TestCase):
    """Test that determine_architectures_to_build correctly interprets hints.
    """

    def assertArchsForHint(self, hint_string, expected_arch_tags,
                           allowed_arch_tags=None, indep_hint_list=None):
        if allowed_arch_tags is None:
            allowed_arch_tags = ['armel', 'hppa', 'i386']
        arch_tags = determine_architectures_to_build(
            hint_string, indep_hint_list, allowed_arch_tags, 'i386',
            True).keys()
        self.assertContentEqual(expected_arch_tags, arch_tags)

    def test_single_architecture(self):
        # A hint string with a single arch resolves to just that arch.
        self.assertArchsForHint('hppa', ['hppa'])

    def test_three_architectures(self):
        # A hint string with multiple archs resolves to just those
        # archs.
        self.assertArchsForHint('amd64 i386 hppa', ['hppa', 'i386'])

    def test_independent(self):
        # 'all' is special, meaning just a single build. The
        # nominatedarchindep architecture is used -- in this case i386.
        self.assertArchsForHint('all', ['i386'])

    def test_one_and_independent(self):
        # 'all' is redundant if we have another build anyway.
        self.assertArchsForHint('hppa all', ['hppa'])

    def test_fictional_and_independent(self):
        # 'all' doesn't make an unbuildable string buildable.
        self.assertArchsForHint('fiction all', [])

    def test_wildcard(self):
        # 'any' is a wildcard that matches all available archs.
        self.assertArchsForHint('any', ['armel', 'hppa', 'i386'])

    def test_kernel_specific_architecture(self):
        # Since we only support Linux-based architectures, 'linux-foo'
        # is treated the same as 'foo'.
        self.assertArchsForHint('linux-hppa', ['hppa'])

    def test_unknown_kernel_specific_architecture(self):
        # Non-Linux architectures aren't supported.
        self.assertArchsForHint('kfreebsd-hppa', [])

    def test_kernel_wildcard_architecture(self):
        # Wildcards work for kernels: 'any-foo' is treated like 'foo'.
        self.assertArchsForHint('any-hppa', ['hppa'])

    def test_kernel_wildcard_architecture_arm(self):
        # The second part of a wildcard matches the canonical CPU name, not
        # on the Debian architecture, so 'any-arm' matches 'armel'.
        self.assertArchsForHint('any-arm', ['armel'])

    def test_kernel_specific_architecture_wildcard(self):
        # Wildcards work for archs too: 'linux-any' is treated like 'any'.
        self.assertArchsForHint('linux-any', ['armel', 'hppa', 'i386'])

    def test_unknown_kernel_specific_architecture_wildcard(self):
        # But unknown kernels continue to result in nothing.
        self.assertArchsForHint('kfreebsd-any', [])

    def test_wildcard_and_independent(self):
        # 'all' continues to be ignored alongside a valid wildcard.
        self.assertArchsForHint('all linux-any', ['armel', 'hppa', 'i386'])

    def test_kernel_independent_is_invalid(self):
        # 'linux-all' isn't supported.
        self.assertArchsForHint('linux-all', [])

    def test_double_wildcard_is_same_as_single(self):
        # 'any-any' is redundant with 'any', but dpkg-architecture supports
        # it anyway.
        self.assertArchsForHint('any-any', ['armel', 'hppa', 'i386'])

    def test_no_all_builds_when_nominatedarchindep_not_permitted(self):
        # Some archives (eg. armel rebuilds) don't want arch-indep
        # builds. If the nominatedarchindep architecture (normally
        # i386) is omitted, no builds will be created for arch-indep
        # sources.
        self.assertArchsForHint('all', [], allowed_arch_tags=['hppa'])

    # TODO: Test arch-indep flag.

    def test_indep_hint_only(self):
        # Some packages need to build arch-indep builds on a specific
        # architecture, declared using XS-Build-Indep-Architecture.
        self.assertArchsForHint('all', ['hppa'], indep_hint_list='hppa')

    def test_indep_hint_only_unsatisfiable(self):
        # An indep hint list that matches nothing results in no builds
        self.assertArchsForHint('all', [], indep_hint_list='fiction')

    def test_indep_hint(self):
        # Unlike nominatedarchindep, a hinted indep will cause an
        # additional build to be created if necessary.
        self.assertArchsForHint(
            'armel all', ['armel', 'hppa'], indep_hint_list='hppa')

    def test_indep_hint_wildcard(self):
        # An indep hint list can include wildcards.
        self.assertArchsForHint(
            'armel all', ['armel', 'hppa'], indep_hint_list='any-hppa')

    def test_indep_hint_coalesces(self):
        # An indep hint list that matches an existing build will avoid
        # creating another.
        self.assertArchsForHint(
            'hppa all', ['hppa'], indep_hint_list='linux-any')

    def test_indep_hint_unsatisfiable(self):
        # An indep hint list that matches nothing results in no
        # additional builds
        self.assertArchsForHint(
            'armel all', ['armel'], indep_hint_list='fiction')
