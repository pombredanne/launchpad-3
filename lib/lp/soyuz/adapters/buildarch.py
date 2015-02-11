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
        return None
    return set(dpkg_architecture.findAllMatches(valid_archs, hint_archs))


def determine_architectures_to_build(hint_list, need_archs,
                                     nominated_arch_indep, need_arch_indep):
    """Return a set of architectures to build.

    :param hint_list: a string of the architectures this source package
        specifies it builds for.
    :param need_archs: an ordered list of all architecture tags that we can
        create builds for. the first usable one gets the arch-indep flag.
    :param nominated_arch_indep: the default architecture tag for
        arch-indep-only packages. may be None.
    :param need_arch_indep: should an arch-indep build be created if possible?
    :return: a map of architecture tag to arch-indep flag for each build
        that should be created.
    """
    build_archs = resolve_arch_spec(hint_list, need_archs)

    if build_archs is None:
        if need_arch_indep and nominated_arch_indep in need_archs:
            # The hint list is just "all". Ask for a nominatedarchindep build.
            build_archs = [nominated_arch_indep]
        else:
            build_archs = []

    build_map = {arch: False for arch in build_archs}

    if need_arch_indep:
        # The ideal arch_indep build is nominatedarchindep. But if we're
        # not creating a build for it, use the first candidate DAS that
        # made it this far.
        if nominated_arch_indep in build_map:
            build_map[nominated_arch_indep] = True
        else:
            for arch in need_archs:
                if arch in build_map:
                    build_map[arch] = True
                    break

    return build_map
