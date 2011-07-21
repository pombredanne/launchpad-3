# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import operator
import os

from sqlobject import SQLObjectNotFound


class BuildDaemonPackagesArchSpecific:
    """Parse and implement "PackagesArchSpecific"."""

    def __init__(self, pas_dir, distroseries):
        self.pas_file = os.path.join(pas_dir, "Packages-arch-specific")
        self.distroseries = distroseries
        self.permit = {}
        self._parsePAS()

    def _parsePAS(self):
        """Parse self.pas_file and construct the permissible arch lists.

        A PAS source line looks like this:

            %openoffice.org2: i386 sparc powerpc amd64

        A PAS binary line looks like this:

            cmucl: i386 sparc amd64
        """
        try:
            fd = open(self.pas_file, "r")
        except IOError:
            return

        all_arch_tags = set([a.architecturetag for a in
                            self.distroseries.architectures])
        for line in fd:
            line = line.split("#")[0]
            line = line.strip()
            if not line:
                continue

            is_source = False
            if line.startswith("%"):
                is_source = True
                line = line[1:]

            pkgname, arch_tags = line.split(":", 1)
            is_exclude = False
            if "!" in arch_tags:
                is_exclude = True
                arch_tags = arch_tags.replace("!", "")

            line_arch_tags = arch_tags.strip().split()
            arch_tags = set(line_arch_tags).intersection(all_arch_tags)
            if is_exclude:
                arch_tags = all_arch_tags - arch_tags

            if not is_source:
                ret = self._handleBinaryPAS(pkgname, arch_tags)
                if ret is None:
                    continue
                pkgname, arch_tags = ret

            self.permit[pkgname] = arch_tags

        fd.close()

    def _handleBinaryPAS(self, binary_name, arch_tags):
        # We need to find a sourcepackagename, so search for it against
        # the nominated distroarchseries (it could be any one, but
        # using this one simplifies testing). If the sourcepackagename
        # changes across arches then we'll have problems. We hope
        # this'll never happen!
        default_architecture = self.distroseries.nominatedarchindep
        try:
            binary_publications = default_architecture.getReleasedPackages(
                binary_name)
        except SQLObjectNotFound:
            # Can't find it at all...
            return None

        if len(binary_publications) == 0:
            # Can't find it, so give up
            return None

        # Use the first binary, they will all point to the same build and
        # consequently to the same source.
        test_binary = binary_publications[0]
        build = test_binary.binarypackagerelease.build

        # If the source produces more than one binary it can't be restricted,
        # The binary PAS line is completely ignored.
        if build.binarypackages.count() > 1:
            return None

        # The source produces a single binary, so it can be restricted.
        source_name = build.source_package_release.name

        # The arch-independent builder /must/ be included in the
        # arch_tags, regardless of whether the binary PAS line allows
        # for it. If it is omitted and the package includes an arch-all
        # binary, that binary will not be built! See thread on Launchpad
        # list during Aug/2006 for more details on discussion. -- kiko
        default_architecture_tag = default_architecture.architecturetag
        if default_architecture_tag not in arch_tags:
            arch_tags.add(default_architecture_tag)

        return source_name, arch_tags


def determineArchitecturesToBuild(pubrec, legal_archseries,
                                  distroseries, pas_verify=None):
    """Return a list of architectures for which this publication should build.

    This function answers the question: given a publication, what
    architectures should we build it for? It takes a set of legal
    distroarchseries and the distribution series for which we are
    building, and optionally a BuildDaemonPackagesArchSpecific
    (informally known as 'P-a-s') instance.

    The P-a-s component contains a list of forbidden architectures for
    each source package, which should be respected regardless of which
    architectures have been requested in the source package metadata,
    for instance:

      * 'aboot' should only build on powerpc
      * 'mozilla-firefox' should not build on sparc

    This black/white list is an optimization to suppress temporarily
    known-failures build attempts and thus saving build-farm time.

    For PPA publications we only consider architectures supported by PPA
    subsystem (`DistroArchSeries`.supports_virtualized flag) and P-a-s is
    turned off to give the users the chance to test their fixes for upstream
    problems.

    :param: pubrec: `ISourcePackagePublishingHistory` representing the
        source publication.
    :param: legal_archseries: a list of all initialized `DistroArchSeries`
        to be considered.
    :param: distroseries: the context `DistroSeries`.
    :param: pas_verify: optional P-a-s verifier object/component.
    :return: a list of `DistroArchSeries` for which the source publication in
        question should be built.
    """
    hint_string = pubrec.sourcepackagerelease.architecturehintlist

    assert hint_string, 'Missing arch_hint_list'

    # Ignore P-a-s for PPA publications.
    if pubrec.archive.is_ppa:
        pas_verify = None

    # The 'PPA supported' flag only applies to virtualized archives
    if pubrec.archive.require_virtualized:
        legal_archseries = [
            arch for arch in legal_archseries if arch.supports_virtualized]
        # Cope with no virtualization support at all. It usually happens when
        # a distroseries is created and initialized, by default no
        # architecture supports its. Distro-team might take some time to
        # decide which architecture will be allowed for PPAs and queue-builder
        # will continue to work meanwhile.
        if not legal_archseries:
            return []

    legal_arch_tags = set(
        arch.architecturetag for arch in legal_archseries if arch.enabled)

    hint_archs = set(hint_string.split())

    # If a *-any architecture wildcard is present, build for everything
    # we can. We only support Linux-based architectures at the moment,
    # and any-any isn't a valid wildcard. See bug #605002.
    if hint_archs.intersection(('any', 'linux-any')):
        package_tags = legal_arch_tags
    else:
        # We need to support arch tags like any-foo and linux-foo, so remove
        # supported kernel prefixes. See bug #73761.
        stripped_archs = hint_archs
        for kernel in ('linux', 'any'):
            stripped_archs = set(
                arch.replace("%s-" % kernel, "") for arch in stripped_archs)
        package_tags = stripped_archs.intersection(legal_arch_tags)

        # 'all' is only used as a last resort, to create an arch-indep
        # build where no builds would otherwise exist.
        if len(package_tags) == 0 and 'all' in hint_archs:
            nominated_arch = distroseries.nominatedarchindep
            if nominated_arch in legal_archseries:
                package_tags = set([nominated_arch.architecturetag])
            else:
                package_tags = set()

    if pas_verify:
        build_tags = set()
        for tag in package_tags:
            sourcepackage_name = pubrec.sourcepackagerelease.name
            if sourcepackage_name in pas_verify.permit:
                permitted = pas_verify.permit[sourcepackage_name]
                if tag not in permitted:
                    continue
            build_tags.add(tag)
    else:
        build_tags = package_tags

    sorted_archseries = sorted(legal_archseries,
                                 key=operator.attrgetter('architecturetag'))
    return [arch for arch in sorted_archseries
            if arch.architecturetag in build_tags]
