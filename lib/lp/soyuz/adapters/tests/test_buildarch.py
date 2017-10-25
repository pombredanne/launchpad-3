# Copyright 2009-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from testtools.matchers import (
    MatchesListwise,
    MatchesStructure,
    )

from lp.soyuz.adapters.buildarch import (
    determine_architectures_to_build,
    DpkgArchitectureCache,
    )
from lp.testing import TestCase
from lp.testing.fixture import CaptureTimeline


class TestDpkgArchitectureCache(TestCase):

    def setUp(self):
        super(TestDpkgArchitectureCache, self).setUp()
        self.timeline = self.useFixture(CaptureTimeline()).timeline

    def assertTimeline(self, expected_details):
        matchers = []
        for expected_detail in expected_details:
            matchers.append(MatchesStructure.byEquality(
                category='dpkg-architecture-start', detail=expected_detail))
            matchers.append(MatchesStructure.byEquality(
                category='dpkg-architecture-stop', detail=expected_detail))
        self.assertThat(self.timeline.actions, MatchesListwise(matchers))

    def test_multiple(self):
        self.assertContentEqual(
            ['amd64', 'armhf'],
            DpkgArchitectureCache().findAllMatches(
                ['amd64', 'i386', 'armhf'], ['amd64', 'armhf']))
        self.assertTimeline([
            '-iamd64 DEB_HOST_ARCH=amd64',
            '-iarmhf DEB_HOST_ARCH=amd64',
            '-iamd64 DEB_HOST_ARCH=i386',
            '-iarmhf DEB_HOST_ARCH=i386',
            '-iamd64 DEB_HOST_ARCH=armhf',
            '-iarmhf DEB_HOST_ARCH=armhf',
            ])

    def test_any(self):
        self.assertContentEqual(
            ['amd64', 'i386', 'kfreebsd-amd64'],
            DpkgArchitectureCache().findAllMatches(
                ['amd64', 'i386', 'kfreebsd-amd64'], ['any']))
        self.assertTimeline([
            '-iany DEB_HOST_ARCH=amd64',
            '-iany DEB_HOST_ARCH=i386',
            '-iany DEB_HOST_ARCH=kfreebsd-amd64',
            ])

    def test_all(self):
        self.assertContentEqual(
            [],
            DpkgArchitectureCache().findAllMatches(
                ['amd64', 'i386', 'kfreebsd-amd64'], ['all']))
        self.assertTimeline([
            '-iall DEB_HOST_ARCH=amd64',
            '-iall DEB_HOST_ARCH=i386',
            '-iall DEB_HOST_ARCH=kfreebsd-amd64',
            ])

    def test_partial_wildcards(self):
        self.assertContentEqual(
            ['amd64', 'i386', 'kfreebsd-amd64'],
            DpkgArchitectureCache().findAllMatches(
                ['amd64', 'i386', 'kfreebsd-amd64', 'kfreebsd-i386'],
                ['linux-any', 'any-amd64']))
        self.assertTimeline([
            '-ilinux-any DEB_HOST_ARCH=amd64',
            '-iany-amd64 DEB_HOST_ARCH=amd64',
            '-ilinux-any DEB_HOST_ARCH=i386',
            '-iany-amd64 DEB_HOST_ARCH=i386',
            '-ilinux-any DEB_HOST_ARCH=kfreebsd-amd64',
            '-iany-amd64 DEB_HOST_ARCH=kfreebsd-amd64',
            '-ilinux-any DEB_HOST_ARCH=kfreebsd-i386',
            '-iany-amd64 DEB_HOST_ARCH=kfreebsd-i386',
            ])


class TestDetermineArchitecturesToBuild(TestCase):
    """Test that determine_architectures_to_build correctly interprets hints.
    """

    def assertArchsForHint(self, hint_string, expected_arch_tags,
                           allowed_arch_tags=None, indep_hint_list=None,
                           need_arch_indep=True):
        if allowed_arch_tags is None:
            allowed_arch_tags = ['armel', 'hppa', 'i386']
        arch_tags = determine_architectures_to_build(
            hint_string, indep_hint_list, allowed_arch_tags, 'i386',
            need_arch_indep)
        self.assertContentEqual(expected_arch_tags.items(), arch_tags.items())

    def test_single_architecture(self):
        # A hint string with a single arch resolves to just that arch.
        self.assertArchsForHint('hppa', {'hppa': True})

    def test_three_architectures(self):
        # A hint string with multiple archs resolves to just those
        # archs.
        self.assertArchsForHint(
            'amd64 i386 hppa', {'hppa': False, 'i386': True})

    def test_independent(self):
        # 'all' is special, meaning just a single build. The
        # nominatedarchindep architecture is used -- in this case i386.
        self.assertArchsForHint('all', {'i386': True})

    def test_one_and_independent(self):
        # 'all' is redundant if we have another build anyway.
        self.assertArchsForHint('hppa all', {'hppa': True})

    def test_fictional_and_independent(self):
        # 'all' doesn't make an unbuildable string buildable.
        self.assertArchsForHint('fiction all', {})

    def test_wildcard(self):
        # 'any' is a wildcard that matches all available archs.
        self.assertArchsForHint(
            'any', {'armel': False, 'hppa': False, 'i386': True})

    def test_kernel_specific_architecture(self):
        # Since we only support Linux-based architectures, 'linux-foo'
        # is treated the same as 'foo'.
        self.assertArchsForHint('linux-hppa', {'hppa': True})

    def test_unknown_kernel_specific_architecture(self):
        # Non-Linux architectures aren't supported.
        self.assertArchsForHint('kfreebsd-hppa', {})

    def test_kernel_wildcard_architecture(self):
        # Wildcards work for kernels: 'any-foo' is treated like 'foo'.
        self.assertArchsForHint('any-hppa', {'hppa': True})

    def test_kernel_wildcard_architecture_arm(self):
        # The second part of a wildcard matches the canonical CPU name, not
        # on the Debian architecture, so 'any-arm' matches 'armel'.
        self.assertArchsForHint('any-arm', {'armel': True})

    def test_kernel_specific_architecture_wildcard(self):
        # Wildcards work for archs too: 'linux-any' is treated like 'any'.
        self.assertArchsForHint(
            'linux-any', {'armel': False, 'hppa': False, 'i386': True})

    def test_unknown_kernel_specific_architecture_wildcard(self):
        # But unknown kernels continue to result in nothing.
        self.assertArchsForHint('kfreebsd-any', {})

    def test_wildcard_and_independent(self):
        # 'all' continues to be ignored alongside a valid wildcard.
        self.assertArchsForHint(
            'all linux-any', {'armel': False, 'hppa': False, 'i386': True})

    def test_kernel_independent_is_invalid(self):
        # 'linux-all' isn't supported.
        self.assertArchsForHint('linux-all', {})

    def test_double_wildcard_is_same_as_single(self):
        # 'any-any' is redundant with 'any', but dpkg-architecture supports
        # it anyway.
        self.assertArchsForHint(
            'any-any', {'armel': False, 'hppa': False, 'i386': True})

    def test_disallowed_nominatedarchindep_falls_back(self):
        # Some archives don't allow nominatedarchindep builds. In that
        # case, one of the other architectures is chosen.
        self.assertArchsForHint(
            'any all', {'hppa': True, 'armel': False},
            allowed_arch_tags=['hppa', 'armel'])
        self.assertArchsForHint(
            'all', {'hppa': True}, allowed_arch_tags=['hppa', 'armel'])

    def test_indep_hint_only(self):
        # Some packages need to build arch-indep builds on a specific
        # architecture, declared using XS-Build-Indep-Architecture.
        self.assertArchsForHint('all', {'hppa': True}, indep_hint_list='hppa')

    def test_indep_hint_only_multiple(self):
        # The earliest available architecture in the available list (not
        # the hint list) is chosen.
        self.assertArchsForHint(
            'all', {'armel': True}, indep_hint_list='armel hppa')
        self.assertArchsForHint(
            'all', {'hppa': True}, indep_hint_list='armel hppa',
            allowed_arch_tags=['hppa', 'armel', 'i386'])

    def test_indep_hint_only_unsatisfiable(self):
        # An indep hint list that matches nothing results in no builds
        self.assertArchsForHint('all', {}, indep_hint_list='fiction')

    def test_indep_hint(self):
        # Unlike nominatedarchindep, a hinted indep will cause an
        # additional build to be created if necessary.
        self.assertArchsForHint(
            'armel all', {'armel': False, 'hppa': True},
            indep_hint_list='hppa')

    def test_indep_hint_wildcard(self):
        # An indep hint list can include wildcards.
        self.assertArchsForHint(
            'armel all', {'armel': False, 'hppa': True},
            indep_hint_list='any-hppa')

    def test_indep_hint_coalesces(self):
        # An indep hint list that matches an existing build will avoid
        # creating another.
        self.assertArchsForHint(
            'hppa all', {'hppa': True}, indep_hint_list='linux-any')

    def test_indep_hint_unsatisfiable(self):
        # An indep hint list that matches nothing results in no
        # additional builds
        self.assertArchsForHint(
            'armel all', {'armel': False}, indep_hint_list='fiction')

    def test_no_need_arch_indep(self):
        self.assertArchsForHint(
            'armel all', {'armel': False}, need_arch_indep=False)

    def test_no_need_arch_indep_hint(self):
        self.assertArchsForHint(
            'armel all', {'armel': False}, indep_hint_list='hppa',
            need_arch_indep=False)

    def test_no_need_arch_indep_only(self):
        self.assertArchsForHint('all', {}, need_arch_indep=False)
