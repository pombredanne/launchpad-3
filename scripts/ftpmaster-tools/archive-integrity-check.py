#!/usr/bin/python
#
# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# Check the integrity of an archive via it's indices files

##############################################################################

import commands
import os
import stat
import sys
from tempfile import NamedTemporaryFile

import apt_pkg

##############################################################################

Filelist = None
ArchiveRoot = "/srv/launchpad.net/ubuntu-archive/ubuntu/"
Count = 0

##############################################################################


def error(msg):
    sys.stderr.write("E: %s\n" % (msg))

##############################################################################


def check_file(filename, md5sum_expected, size_expected):
    global Count

    # Check existence/readability
    if os.access(filename, os.R_OK) == 0:
        if os.path.exists(filename):
            error("%s could not be read (permission denied)" \
                  % (filename))
        else:
            error("%s is missing" % (filename))
        return

    # Check md5sum
    filehandle = open(filename)
    md5sum_found = apt_pkg.md5sum(filehandle)
    if md5sum_found != md5sum_expected:
        error("%s failed md5sum check ('%s' vs '%s')" \
              % (filename, md5sum_expected, md5sum_found))
    filehandle.close()
    # Check size
    size_found = os.stat(filename)[stat.ST_SIZE]
    size_expected = int(size_expected)
    if size_found != size_expected:
        error("%s failed size check (expected: %d, got: %d)" \
              % (filename, size_expected, size_found))

    Count += 1
    if Count % 10 == 0:
        sys.stdout.write(".")
        sys.stdout.flush()

##############################################################################


def validate_sources(sources_filename, suite, component):
    if suite == "dapper":
        return
    sys.stdout.write("Checking %s/%s/source: " % (suite, component))
    sys.stdout.flush()
    # apt_pkg.ParseTagFile needs a real file handle and can't handle a
    # GzipFile instance...
    sources = NamedTemporaryFile()
    (result, output) = commands.getstatusoutput("gunzip -c %s > %s" \
                                                % (sources_filename,
                                                   sources.name))
    if (result != 0):
        sys.stderr.write("Gunzip invocation failed!\n%s\n" % (output))
        sys.exit(result)
    sources.seek(0)
    Sources = apt_pkg.ParseTagFile(sources)
    while Sources.Step():
        directory = Sources.Section.Find('Directory')
        files = Sources.Section.Find('Files')
        for i in files.split('\n'):
            (md5sum_expected, size_expected, name) = i.split()
            filename = os.path.join(ArchiveRoot, directory, name)
            check_file(filename, md5sum_expected, size_expected)
    sys.stdout.write("done.\n")
    sys.stdout.flush()
    sources.close()

##############################################################################


def validate_packages(packages_filename, suite, component, architecture):
    if suite == "dapper":
        return

    sys.stdout.write("Checking %s/%s/%s: " % (suite, component, architecture))
    sys.stdout.flush()
    # apt_pkg.ParseTagFile needs a real file handle and can't handle a
    # GzipFile instance...
    packages = NamedTemporaryFile()
    (result, output) = commands.getstatusoutput("gunzip -c %s > %s"
                                                % (packages_filename,
                                                   packages.name))
    if (result != 0):
        sys.stderr.write("Gunzip invocation failed!\n%s\n" % (output))
        sys.exit(result)
    packages.seek(0)
    Packages = apt_pkg.ParseTagFile(packages)
    while Packages.Step():
        md5sum_expected = Packages.Section.Find('MD5sum')
        size_expected = Packages.Section.Find('Size')
        filename = Packages.Section.Find('Filename')
        filename = os.path.join(ArchiveRoot, filename)
        check_file(filename, md5sum_expected, size_expected)

    sys.stdout.write("done.\n")
    sys.stdout.flush()
    packages.close()

##############################################################################


def _process_dir(_, dirname, filenames):
    global Filelist

    for filename in filenames:
        if filename == "Packages.gz" or filename == "Sources.gz":
            split = dirname.split('/')
            if split[-2] == "debian-installer":
                (suite, component, _, architecture) = split[-4:]
            else:
                (suite, component, architecture) = split[-3:]
            architecture = architecture.replace("binary-", "")
            full_filename = os.path.join(dirname, filename)
            if architecture == "source":
                validate_sources(full_filename, suite, component)
            else:
                validate_packages(
                    full_filename, suite, component, architecture)

##############################################################################


def main():
    global Filelist

    Filelist = {}
    apt_pkg.init()

    os.path.walk(os.path.join(ArchiveRoot, "dists"),
                 _process_dir, None)

    return 0

##############################################################################

if __name__ == '__main__':
    sys.exit(main())
