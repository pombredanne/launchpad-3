# Copyright 2009-2013 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'determine_architectures_to_build',
    ]


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


def resolve_arch_spec(hintlist, valid_archs):
    hint_archs = set(hintlist.split())
    # 'all' is only used if it's a purely arch-indep package.
    if hint_archs == set(["all"]):
        return set(), True
    return (
        set(dpkg_architecture.findAllMatches(valid_archs, hint_archs)), False)


def determine_architectures_to_build(hint_list, indep_hint_list, need_archs,
                                     nominated_arch_indep, need_arch_indep):
    """Return a set of architectures to build.

    :param hint_list: a string of the architectures this source package
        specifies it builds for.
    :param indep_hint_list: a string of the architectures this source package
        specifies it can build architecture-independent packages on.
    :param need_archs: an ordered list of all architecture tags that we can
        create builds for. the first usable one gets the arch-indep flag.
    :param nominated_arch_indep: the default architecture tag for
        arch-indep-only packages. may be None.
    :param need_arch_indep: should an arch-indep build be created if possible?
    :return: a map of architecture tag to arch-indep flag for each build
        that should be created.
    """
    build_archs, indep_only = resolve_arch_spec(hint_list, need_archs)

    # Use the indep hint list if it's set, otherwise fall back to the
    # main architecture list. If that's not set either (ie. it's just
    # "all"), allow any available arch to be chosen.
    if indep_hint_list:
        indep_archs, _ = resolve_arch_spec(indep_hint_list, need_archs)
    elif not indep_only:
        indep_archs = set(build_archs)
    else:
        indep_archs = set(need_archs)

    indep_arch = None
    if need_arch_indep:
        # Try to avoid adding a new build if an existing one would work.
        both_archs = set(build_archs) & set(indep_archs)
        if both_archs:
            indep_archs = both_archs

        # The ideal arch_indep build is nominatedarchindep. But if we're
        # not creating a build for it, use the first candidate DAS that
        # made it this far.
        for arch in [nominated_arch_indep] + need_archs:
            if arch in indep_archs:
                indep_arch = arch
                break

    # Ensure that we build the indep arch.
    if indep_arch is not None and indep_arch not in build_archs:
        build_archs.add(indep_arch)

    return {arch: arch == indep_arch for arch in build_archs}
