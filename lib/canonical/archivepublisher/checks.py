# Copyright: Copyright (C) 2004 Canonical Ltd
# Author: James Troup <james.troup@canonical.com>

################################################################################

import errno, os, re, shutil, string, tempfile
import apt_pkg
from canonical.archivepublisher.GPGV import verify_signed_file
from canonical.archivepublisher.GPGV import VerificationError
from canonical.archivepublisher.TagFiles import parse_tagfile
from canonical.archivepublisher.TagFiles import TagFileParseError
from canonical.archivepublisher.utils import build_file_list
from canonical.archivepublisher.utils import fix_maintainer
from canonical.archivepublisher.utils import ParseMaintError

################################################################################

re_valid_pkg_name = re.compile(r"^[\dA-Za-z][\dA-Za-z\+\-\.]+$")
re_valid_version = re.compile(r"^([0-9]+:)?[0-9A-Za-z\.\-\+:]+$")
re_epoch = re.compile(r"^\d+\:")

class UploadCheckFatal(Exception):
    """This exception is raised if an UploadCheck function encounters a fatal error."""
    pass

__metaclass__ = type
class UploadCheck:
    def __init__(self):
        self.reject_message = ""
        self.directory = None
        self.changes_filename = ""
        self.keyring = ""
        self.dsc_files = {}

    def str_isnum (self, s):
        """Returns true if 's' contains only numbers."""
        if not s:
            return 0
        for c in s:
            if c not in string.digits:
                return 0
        return 1

    def reject (self, s, prefix="REJECTED: "):
        """Append 's' as a new line to the rejection message.  If 'prefix' is
non-null use that as a prefix in place of the default ('REJECTED:
').
"""
        if s:
            self.reject_message += prefix + s + "\n"

    def absname (self, filename):
        if self.directory:
            filename = os.path.join(self.directory, filename)
        return filename

    ############################################################
    #
    # generic

    def val_sig(self, filename):
        """Validate the signature on a file."""
        try:
            filename = self.absname(filename)
            verify_signed_file(filename, [self.keyring])
        except VerificationError, reason:
            self.reject(str(reason))

    def val_email(self, field, field_name, filename):
        """Validate 'email address' style fields (e.g. 'Maintainer', 'Changed-By')."""
        try:
            (unused, unused, unused, unused) = fix_maintainer(field, field_name)
        except ParseMaintError, reason:
            self.reject("%s: %s" \
                   % (filename, reason))

    ############################################################
    #
    # changes

    def changes_parse(self):
        """Parse a .changes file."""
        try:
            filename = self.absname(self.changes_filename)
            self.changes = parse_tagfile(filename)
        except TagFileParseError, reason:
            self.reject(str(reason))

    def changes_val_mandatory(self):
        """Ensure the mandatory fields exist in the .changes file."""
        mandatory = [ "source", "binary", "architecture", "version",
                      "distribution", "maintainer", "files", "changes" ]
        for field in mandatory:
            if not self.changes.has_key(field):
                self.reject("%s: missing mandatory field '%s'"
                            % (self.changes_filename, field.title()))

    def changes_val_closes(self):
        """Ensure entries in the 'Closes' field in the .changes file are only numbers."""
        for num in self.changes.get("closes", "").split():
            if not self.str_isnum(num):
                self.reject("%s: '%s' in 'Closes' field isn't a number"
                            % (self.changes_filename, num))

    def changes_val_files(self):
        """Ensure the 'Files' field in the .changes is non-empty."""
        if not self.changes["files"]:
            self.reject("%s: 'Files' field is empty" % (self.changes_filename))

    def changes_val_source_exists(self):
        """Ensure that if a .changes file lists 'source' in the 'Architecture'
field that there is a .dsc mentioned in the 'Files' field.
"""
        if "source" in self.changes["architecture"].split():
            have_dsc = 0
            for filename in self.files:
                if filename.endswith(".dsc"):
                    have_dsc = 1
                    break
            if not have_dsc:
                self.reject("%s: no source found and 'Architecture' contains 'source'"
                            % (self.changes_filename))

    ############################################################
    #
    # files

    def files_build(self, parsed_tag_file, is_dsc=False):
        """Build a 'files' dictionary based on a 'Files' field from a .dsc or .changes."""
        files = {}
        try:
            files = build_file_list(parsed_tag_file, is_dsc)
        except ValueError, reason:
            self.reject(str(reason))
        return files

    def files_val_source(self):
        """Ensure that there is only one source package in the upload and that if
there is a .dsc, there is also a .diff.gz.
"""
        dsc = 0
        diff_gz = 0
        tar_gz = 0
        for filename in self.files:
            if filename.endswith(".dsc"):
                dsc += 1
            elif filename.endswith(".diff.gz"):
                diff_gz += 1
            elif filename.endswith(".tar.gz"):
                tar_gz += 1
        if dsc > 1:
            self.reject("%s: only one source package per .changes (> 1 .dsc found)" % self.changes_filename)
        if diff_gz > 1:
            self.reject("%s: only one source package per .changes (> 1 .diff.gz found)" % self.changes_filename)
        if tar_gz > 1:
            self.reject("%s: only one source package per .changes (> 1 .tar.gz found)" % self.changes_filename)

        if dsc and not diff_gz:
            self.reject("%s: .dsc but no .diff.gz" % self.changes_filename)

    ############################################################
    #
    # dsc

    def dsc_get_filename(self):
        """Find the filename of the .dsc from the .changes."""
        for filename in self.files.keys():
            if filename.endswith(".dsc"):
                self.dsc_filename = filename

    def dsc_parse(self):
        """Parse a .dsc file."""
        try:
            filename = self.absname(self.dsc_filename)
            self.dsc = parse_tagfile(filename, dsc_whitespace_rules=1)
        except TagFileParseError, reason:
            self.reject(str(reason))

    def dsc_val_mandatory(self):
        """Ensure the mandatory fields exist in the .dsc file."""
        mandatory = [ "architecture", "binary", "files", "format", "maintainer",
                      "source", "version" ]
        for field in mandatory:
            if not self.dsc.has_key(field):
                self.reject("%s: missing mandatory field '%s'"
                            % (self.dsc_filename, field.title()))

    def dsc_val_source(self):
        """Validate the 'Source' field of a .dsc file."""
        if not re_valid_pkg_name.match(self.dsc["source"]):
            self.reject("%s: invalid source name '%s'" % (self.dsc_filename, self.dsc["source"]))

    # ??? this doesn't enforce policy fully, e.g. 'a:6', 'foo45',
    # '4-5-6' are all considered valid
    def dsc_val_version(self):
        """Validate the 'Version' field of a .dsc file."""
        if not re_valid_version.match(self.dsc["version"]):
            self.reject("%s: invalid version number '%s'" % (self.dsc_filename, self.dsc["version"]))

    def dsc_val_format(self):
        """Validate the 'Format' field of a .dsc file.
['dpkg-source' can currently only extract '1.0' format source packages]
"""
        if self.dsc["format"] != "1.0":
            self.reject("%s: incompatible source package format '%s' in 'Format' field" \
                        % (self.dsc_filename, self.dsc["format"]))

    def dsc_val_build_dep(self, field_name):
        field = self.dsc.get(field_name)
        if not field:
            return
        
        # Check for historical dpkg-dev breakage
        if field.startswith("ARRAY"):
            self.reject("%s: invalid '%s' field produced by broken dpkg-dev" \
                   % (self.dsc_filename, field_name.title()))

        # Have [python-]apt try to parse them...
        try:
            apt_pkg.ParseSrcDepends(field)
        except:
            self.reject("%s: invalid '%s' field can not be parsed by apt" \
                   % (self.dsc_filename, field_name.title()))
            pass

    def dsc_version_against_changes(self):
        """Ensure the version number in the .dsc matches the version number in
the .changes.
"""
        if self.dsc["version"] != self.changes["version"]:
            self.reject("%s: version '%s' does not match '%s' from .changes" \
                        % (self.dsc_filename, self.dsc["version"], self.changes["version"]))

    def dsc_val_files(self):
        """Ensure that there is 1 and only 1 .dsc, .diff.gz and [.orig].tar.gz
mentioned in the .dsc
"""
        diff_gz = 0
        tar_gz = 0
        for filename in self.dsc_files:
            if filename.endswith(".diff.gz"):
                diff_gz += 1
            elif filename.endswith(".tar.gz"):
                tar_gz += 1
            else:
                self.reject("%s: unrecognised file '%s' in 'Files' field" \
                            % (self.dsc_filename, filename))

        if diff_gz > 1:
            self.reject("%s: more than one .diff.gz in 'Files' field" % self.dsc_filename)
        if tar_gz > 1:
            self.reject("%s: more than one .tar.gz in 'Files' field" % self.dsc_filename)

        # Too little
        if not diff_gz:
            self.reject("%s: no .diff.gz in 'Files' field" % self.dsc_filename)
        if not tar_gz:
            self.reject("%s: no .tar.gz or .orig.tar.gz in 'Files' field" % self.dsc_filename)

    # ??? FIXME
    # ??? requires pkg.orig.tar.gz to be around
    # ??? rename
    # ??? fix doc string
    # ??? add check on changelog parsing??
    def get_changelog_versions(source_dir):
        """Extracts a the source package and (optionally) grabs the
        version history out of debian/changelog for the BTS."""

        # Find the .dsc (again)
        dsc_filename = None;
        for file in files.keys():
            if files[file]["type"] == "dsc":
                dsc_filename = file;

        # If there isn't one, we have nothing to do. (We have reject()ed the upload already)
        if not dsc_filename:
            return;

        # Create a symlink mirror of the source files in our temporary directory
        for f in files.keys():
            m = utils.re_issource.match(f);
            if m:
                src = os.path.join(source_dir, f);
                # If a file is missing for whatever reason, give up.
                if not os.path.exists(src):
                    return;
                type = m.group(3);
                if type == "orig.tar.gz" and pkg.orig_tar_gz:
                    continue;
                dest = os.path.join(os.getcwd(), f);
                os.symlink(src, dest);

        # If the orig.tar.gz is not a part of the upload, create a symlink to the
        # existing copy.
        if pkg.orig_tar_gz:
            dest = os.path.join(os.getcwd(), os.path.basename(pkg.orig_tar_gz));
            os.symlink(pkg.orig_tar_gz, dest);

        # Extract the source
        cmd = "dpkg-source -sn -x %s" % (dsc_filename);
        (result, output) = commands.getstatusoutput(cmd);
        if (result != 0):
            reject("'dpkg-source -x' failed for %s [return code: %s]." % (dsc_filename, result));
            reject(utils.prefix_multi_line_string(output, " [dpkg-source output:] "), "");
            return;

        if not Cnf.Find("Dir::Queue::BTSVersionTrack"):
            return;

        # Get the upstream version
        upstr_version = utils.re_no_epoch.sub('', dsc["version"]);
        if re_strip_revision.search(upstr_version):
            upstr_version = re_strip_revision.sub('', upstr_version);

        # Ensure the changelog file exists
        changelog_filename = "%s-%s/debian/changelog" % (dsc["source"], upstr_version);
        if not os.path.exists(changelog_filename):
            reject("%s: debian/changelog not found in extracted source." % (dsc_filename));
            return;


    def check_source_package(self):
        tmpdir = tempfile.mkdtemp()
        cwd = os.getcwd()
        os.chdir(tmpdir)

        # ??? get_changelog_versions(cwd)

        os.chdir(cwd)
        try:
            shutil.rmtree(tmpdir)
        except OSError, e:
            if errno.errorcode[e.errno] != 'EACCES':
                raise UploadCheckFatal("%s: couldn't remove source tree."
                                       % (self.dsc_filename))

            self.reject("%s: source tree could not be cleanly removed." % self.dsc_filename)
            # We probably have u-r or u-w directories so chmod everything
            # and try again.
            cmd = "chmod -R u+rwx %s" % (tmpdir)
            result = os.system(cmd)
            if result != 0:
                raise UploadCheckFatal("%s: '%s' failed with exit code %s."
                                       % (self.dsc_filename, cmd, result))
            shutil.rmtree(tmpdir)
        except:
            raise UploadCheckFatal("%s: couldn't remove source tree."
                                   % (self.dsc_filename))

    ########################################

#  * Validate the source package by extracting it ('dpkg-source -x')
#  * Ensure resulting source package can be removed
#  * Ensure debian/changelog exists

#  * Check version against other suites
#  * Check files against copies already (md5sum+size) in the archive/queue

    ############################################################

    def check(self, changes_filename):
        self.changes_filename = changes_filename

        # ??? - should not do further tests after any of these?
        self.val_sig(self.changes_filename)
        self.changes_parse()
        self.files = self.files_build(self.changes)
        self.changes_val_mandatory()
        self.changes_val_files()
        # ???

        self.val_email(self.changes["maintainer"], "Maintainer", self.changes_filename)
        if self.changes.get("changed-by"):
            self.val_email(self.changes["changed-by"], "Changed-By", self.changes_filename)
        self.changes_val_closes()
        self.changes_val_source_exists()
        self.files_val_source()

################################################################################
