# Copyright 2009-2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'determine_architectures_to_build',
    ]


from operator import attrgetter
import os
import subprocess


class DpkgArchitectureCache:
    """Cache the results of asking questions of dpkg-architecture."""

    def __init__(self):
        self._matches = {}

    def match(self, arch, wildcard):
        if (arch, wildcard) not in self._matches:
            command = ["dpkg-architecture", "-i%s" % wildcard]
            env = dict(os.environ)
            env["DEB_HOST_ARCH"] = arch
            ret = (subprocess.call(command, env=env) == 0)
            self._matches[(arch, wildcard)] = ret
        return self._matches[(arch, wildcard)]

    def findAllMatches(self, arches, wildcards):
        return list(sorted(set(
            arch for arch in arches for wildcard in wildcards
            if self.match(arch, wildcard))))


dpkg_architecture = DpkgArchitectureCache()


def find_valid_architectures(hintlist, archive, distroseries,
                             legal_archseries):
    # The 'PPA supported' flag only applies to virtualized archives
    candidates = list(legal_archseries)
    if archive.require_virtualized:
        candidates = [
            arch for arch in candidates if arch.supports_virtualized]
    return set(
        arch.architecturetag for arch in candidates if arch.enabled)


def determine_architectures_to_build(hintlist, archive, distroseries,
                                     legal_archseries, need_arch_indep):
    """Return a set of architectures for which this publication should build.

    This function answers the question: given a list of architectures and
    an archive, what architectures should we build it for? It takes a set of
    legal distroarchseries and the distribution series for which we are
    building.

    For PPA publications we only consider architectures supported by PPA
    subsystem (`DistroArchSeries`.supports_virtualized flag).

    :param: hintlist: A string of the architectures this source package
        specifies it builds for.
    :param: archive: The `IArchive` we are building into.
    :param: distroseries: the context `DistroSeries`.
    :param: legal_archseries: a list of all initialized `DistroArchSeries`
        to be considered.
    :return: a set of `DistroArchSeries` for which the source publication in
        question should be built.
    """
    archs = find_valid_architectures(
        hintlist, archive, distroseries, legal_archseries)
    if not archs:
        return []

    hint_archs = set(hintlist.split())
    build_tags = set(dpkg_architecture.findAllMatches(archs, hint_archs))

    # 'all' is only used as a last resort, to create an arch-indep build
    # where no builds would otherwise exist.
    if need_arch_indep and len(build_tags) == 0 and 'all' in hint_archs:
        nominated_arch = distroseries.nominatedarchindep
        if nominated_arch in legal_archseries:
            build_tags = set([nominated_arch.architecturetag])
        else:
            build_tags = set()

    return set(a for a in legal_archseries if a.architecturetag in build_tags)
