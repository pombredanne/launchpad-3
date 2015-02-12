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


def determine_architectures_to_build(hintlist, valid_archs,
                                     nominated_arch_indep, need_arch_indep):
    """Return a set of architectures to build.

    :param hintlist: A string of the architectures this source package
        specifies it builds for.
    :param valid_archs: a list of all architecture tags that we can
        create builds for.
    :param nominated_arch_indep: a preferred architecture tag for
        architecture-independent builds. May be None.
    :return: a set of architecture tags for which the source publication in
        question should be built.
    """
    hint_archs = set(hintlist.split())
    build_archs = set(
        dpkg_architecture.findAllMatches(valid_archs, hint_archs))

    # 'all' is only used as a last resort, to create an arch-indep build
    # where no builds would otherwise exist.
    if need_arch_indep and len(build_archs) == 0 and 'all' in hint_archs:
        if nominated_arch_indep in valid_archs:
            return set([nominated_arch_indep])
        else:
            return set()

    return build_archs
