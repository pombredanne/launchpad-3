# Copyright Canonical Limited 2004-2006

import os

from sqlobject import SQLObjectNotFound

class BuildDaemonPackagesArchSpecific:
    """Parse and implement "PackagesArchSpecific"."""

    def __init__(self, pas_dir, distrorelease):
        self.pas_file = os.path.join(pas_dir, "Packages-arch-specific")
        self.distrorelease = distrorelease
        self.permit = {}
        self._parsePAS()

    def _parsePAS(self):
        """Parse self.pas_file and construct the permissible arch lists.

        A PAS source line looks like this:

            %openoffice.org2: i386 sparc powerpc amd64
        """
        try:
            fd = open(self.pas_file, "r")
        except IOError:
            return

        all_archs = set([a.architecturetag for a in
                         self.distrorelease.architectures])
        for line in fd:
            if "#" in line:
                line = line[:line.find("#")]
            line = line.strip()
            if not line:
                continue
            is_source = False
            if line.startswith("%"):
                is_source = True
                line = line[1:]
            else:
                # XXX: dsilvers: 20060201: This is here because otherwise
                # we have too many false positives for now. In time we need
                # to change the section below to use the binary line from
                # the dsc instead of the publishing records. But this is
                # currently not in the database. Bug#30264
                continue
            pkgname, archs = line.split(":", 1)
            is_exclude = False
            if "!" in archs:
                is_exclude = True
                archs = archs.replace("!", "")
            line_archs = archs.strip().split()
            archs = set(line_archs).intersection(all_archs)
            if is_exclude:
                archs = all_archs - archs
            if not archs:
                # None of the architectures listed affect us.
                if is_source:
                    # But if it's a src pkg then we can still use the
                    # information
                    self.permit[pkgname] = set()
                continue

            if not is_source:
                # We need to find a sourcepackagename, so pick an arch
                # to locate it on.
                arch = iter(archs).next()
                distroarchrelease = self.distrorelease[arch]
                try:
                    # If the sourcepackagename changes across arch then
                    # we'll have problems. We assume this'll never happen
                    pkgs = distroarchrelease.getReleasedPackages(pkgname)
                except SQLObjectNotFound:
                    # Can't find it at all...
                    continue
                if not pkgs:
                    # Can't find it, so give up
                    continue
                pkg = pkgs[0].binarypackagerelease
                src_pkg = pkg.build.sourcepackagerelease
                pkgname = src_pkg.sourcepackagename.name

            self.permit[pkgname] = archs

        fd.close()


