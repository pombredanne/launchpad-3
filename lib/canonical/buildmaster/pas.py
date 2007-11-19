# Copyright Canonical Limited 2004-2006

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

    def _handleBinaryPAS(self, pkgname, arch_tags):
        # We need to find a sourcepackagename, so search for it against
        # the nominated distroarchseries (it could be any one, but
        # using this one simplifies testing). If the sourcepackagename
        # changes across arches then we'll have problems. We hope
        # this'll never happen!
        arch_indep_dar = self.distroseries.nominatedarchindep
        try:
            pkgs = arch_indep_dar.getReleasedPackages(pkgname)
        except SQLObjectNotFound:
            # Can't find it at all...
            return None
        if not pkgs:
            # Can't find it, so give up
            return None
        pkg = pkgs[0].binarypackagerelease
        src_pkg = pkg.build.sourcepackagerelease
        pkgname = src_pkg.sourcepackagename.name

        # The arch-independent builder /must/ be included in the
        # arch_tags, regardless of whether the binary PAS line allows
        # for it. If it is omitted and the package includes an arch-all
        # binary, that binary will not be built! See thread on Launchpad
        # list during Aug/2006 for more details on discussion. -- kiko
        arch_indep_tag = arch_indep_dar.architecturetag
        if arch_indep_tag not in arch_tags:
            arch_tags.add(arch_indep_tag)

        return pkgname, arch_tags

