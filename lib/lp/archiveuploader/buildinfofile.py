# Copyright 2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Build information files."""

__metaclass__ = type

__all__ = [
    'BuildInfoFile',
    ]

from lp.app.errors import NotFoundError
from lp.archiveuploader.dscfile import SignableTagFile
from lp.archiveuploader.nascentuploadfile import PackageUploadFile
from lp.archiveuploader.utils import (
    re_isbuildinfo,
    re_no_epoch,
    UploadError,
    )


class BuildInfoFile(PackageUploadFile, SignableTagFile):
    """Represents an uploaded build information file."""

    def __init__(self, filepath, checksums, size, component_and_section,
                 priority_name, package, version, changes, policy, logger):
        super(BuildInfoFile, self).__init__(
            filepath, checksums, size, component_and_section, priority_name,
            package, version, changes, policy, logger)
        self.parse(verify_signature=not policy.unsigned_buildinfo_ok)
        arch_match = re_isbuildinfo.match(self.filename)
        self.architecture = arch_match.group(3)

    @property
    def is_sourceful(self):
        # XXX cjwatson 2017-03-29: We should get this from the parsed
        # Architecture field instead.
        return self.architecture == "source"

    @property
    def is_binaryful(self):
        # XXX cjwatson 2017-03-29: We should get this from the parsed
        # Architecture field instead.
        return self.architecture != "source"

    @property
    def is_archindep(self):
        # XXX cjwatson 2017-03-29: We should get this from the parsed
        # Architecture field instead.
        return self.architecture == "all"

    def verify(self):
        """Verify the uploaded buildinfo file.

        It returns an iterator over all the encountered errors and warnings.
        """
        self.logger.debug("Verifying buildinfo file %s" % self.filename)

        version_chopped = re_no_epoch.sub('', self.version)
        buildinfo_match = re_isbuildinfo.match(self.filename)
        filename_version = buildinfo_match.group(2)
        if filename_version != version_chopped:
            yield UploadError("%s: should be %s according to changes file."
                % (filename_version, version_chopped))

    def checkBuild(self, build):
        """See `PackageUploadFile`."""
        try:
            das = self.policy.distroseries[self.architecture]
        except NotFoundError:
            raise UploadError(
                "Upload to unknown architecture %s for distroseries %s" %
                (self.architecture, self.policy.distroseries))

        # Sanity check; raise an error if the build we've been
        # told to link to makes no sense.
        if (build.pocket != self.policy.pocket or
            build.distro_arch_series != das or
            build.archive != self.policy.archive):
            raise UploadError(
                "Attempt to upload buildinfo specifying build %s, where it "
                "doesn't fit." % build.id)

    def storeInDatabase(self):
        """Create and return the corresponding `LibraryFileAlias` reference."""
        with open(self.filepath, "rb") as f:
            return self.librarian.create(
                self.filename, self.size, f, self.content_type,
                restricted=self.policy.archive.private)
