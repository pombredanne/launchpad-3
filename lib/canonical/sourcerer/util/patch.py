#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# arch-tag: 981b6e8a-fd95-4862-b9b8-1fc7a82f2db0
"""Parse patch files.

This module contains a class to parse patch files and a function to apply
one to a directory.
"""

__copyright__ = "Copyright © 2004 Canonical Software."
__author__    = "Scott James Remnant <scott@canonical.com>"


import os
import sys
import bz2
import gzip


class PatchError(Exception): pass
class PatchApplyError(Exception): pass

class PatchFile(object):
    """Patch file.

    This class is able to parse both unified and context diffs to
    discover what files they patch.  It can't handle traditional or
    ed-style patches, but then those are evil and we never want to
    encounter them.

    Properties:
      patched   List of filenames patched
      patchsrc  List of filenames to be patched
    """

    def __init__(self, filename=None, fileobj=None):
        self.patched = []
        self.patchsrc = []

        if fileobj is not None:
            self.parse(fileobj)
        elif filename is not None:
            self.open(filename)

    def __iter__(self):
        """Iterate the patched files."""
        return iter(self.patched)

    def open(self, filename):
        """Open and parse a patch file."""
        if filename.endswith(".bz2"):
            f = bz2.BZ2File(filename)
            try:
                self.parse(f)
            finally:
                f.close()

        elif filename.endswith(".gz"):
            f = gzip.open(filename)
            try:
                self.parse(f)
            finally:
                f.close()

        else:
            f = open(filename)
            try:
                self.parse(f)
            finally:
                f.close()

    def parse(self, f):
        """Parse a patch file.

        This largely ignores anything it doesn't like the look of,
        on the basis that patches should be clean *anyway*.  We can trip
        up and LART on a case-by-case basis.
        """
        for line in f:
            if line.startswith("--- "):
                # Unified diff
                expect_next = "+++ "
            elif line.startswith("*** "):
                # Context diff
                expect_next = "--- "
            else:
                continue

            try:
                old_file = line.rstrip()[4:]
                old_file = old_file[:old_file.index("\t")]
            except:
                pass

            try:
                new_line = f.next()
                if not new_line.startswith(expect_next):
                    continue
            except StopIteration:
                continue

            try:
                new_file = new_line.rstrip()[4:]
                new_file = new_file[:new_file.index("\t")]
            except:
                pass

            self.patched.append(new_file)
            self.patchsrc.append(old_file)


def apply(patch, dest, prune=1, fussy=False):
    """Apply the patch to a directory.

    The number of initial directory components from each file in the
    patch specified in prune will be stripped before application.  If
    fussy is set then no fuzz will be permitted when applying the patch.
    """
    cmd = [ "patch", "-stN", "--no-backup-if-mismatch" ]
    if prune: cmd.append("-p%d" % prune)
    if fussy: cmd.append("-F0")

    pid = os.fork()
    if pid == 0:
        if patch.endswith(".bz2"):
            inputfile = os.popen("bunzip2 -c %s" % patch, "r")
        elif patch.endswith(".gz"):
            inputfile = os.popen("gunzip -c %s" % patch, "r")
        else:
            inputfile = open(patch, "r")

        os.dup2(inputfile.fileno(), sys.stdin.fileno())

        os.chdir(dest)
        os.execvp(cmd[0], cmd)
        sys.exit(250)
    elif pid > 0:
        (pid, status) = os.wait()

        if not os.WIFEXITED(status):
            raise PatchApplyError, "patch sub-process exited abnormally"
        elif os.WEXITSTATUS(status) == 250:
            raise PatchApplyError, "Unable to execute patch sub-process"
        elif os.WEXITSTATUS(status):
            raise PatchApplyError, "patch sub-process failed"
    else:
        raise PatchApplyError, "Unable to start patch sub-process"
