#! /usr/bin/env python2.4

"""Re-upload translations from given packages."""

__metaclass__ = type

import logging
import operator
import re
import sys

from zope.component import getUtility

from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.sourcepackage import ISourcePackageFactory
from lp.registry.interfaces.sourcepackagename import (
    ISourcePackageNameSet)
from lp.soyuz.interfaces.publishing import PackagePublishingStatus
from lp.soyuz.interfaces.queue import (
    IPackageUploadSet, PackageUploadCustomFormat)


class InputFormatError(Exception):
    """Something wrong with input file contents."""


def get_package_from_line(line):
    """Parse a line from the input file, return `SourcePackage`."""
    ubuntu = getUtility(IDistributionSet).getByName('ubuntu')
    factory = getUtility(ISourcePackageFactory)
    nameset = getUtility(ISourcePackageNameSet)

    line = re.sub('#.*$', '', line).strip()
    components = line.split()
    if len(components) == 0:
        return None
    if len(components) != 2:
        raise InputFormatError(
            "Line does not contain exactly one distroseries name and "
            "one package name: '%s'" % line)

    distroseries_name, package_name = tuple(components)

    distroseries = ubuntu.getSeries(distroseries_name)
    sourcepackagename = nameset.queryByName(package_name)

    return factory.new(distroseries, sourcepackagename)


def get_packages(input_file):
    """Get each of the packages described in `input_file`."""
    packages = []
    for line in input_file:
        package = get_package_from_line(line)
        if package is not None:
            packages.append(package)

    return packages


def get_upload_aliases(package):
    """Get `LibraryFileAlias`es for package's translation upload(s)."""
    our_format = PackageUploadCustomFormat.ROSETTA_TRANSLATIONS
    uploadset = getUtility(IPackageUploadSet)

    packagename = package.sourcepackagename.name
    displayname = package.displayname

    distroseries = package.distroseries
    distro = distroseries.distribution
    histories = distro.main_archive.getPublishedSources(
        name=packagename, distroseries=distroseries,
        status=PackagePublishingStatus.PUBLISHED, exact_match=True)
    histories = list(histories)
    assert len(histories) <= 1, "Multiple published histories!"
    if len(histories) == 0:
        logging.info("No published history entry for %s." % displayname)
        return

    history = histories[0]
    release = history.sourcepackagerelease
    uploadsource = uploadset.getSourceBySourcePackageReleaseIDs([release.id])
    upload = uploadsource.packageupload
    custom_files = [
        custom
        for custom in upload.customfiles if
        custom.format == our_format
        ]

    if len(custom_files) == 0:
        logging.info("No translations upload for %s." % displayname)
    elif len(custom_files) > 1:
        logging.info("Found %d uploads for %s" % (
            len(custom_files), displayname))

    custom_files.sort(key=operator.attrgetter('date_created'))

    return [custom.libraryfilealias for custom in custom_files]


def process_package(package):
    """Get translations for `package` re-uploaded."""
# XXX: Implement
    print get_upload_aliases(package)


def main():
    """Run script.

    Usage: <script> <listing file>

    The <listing file> is a file containing one package per line, in the
    form <Ubuntu release name> <source package name>.

    An Ubuntu release name is of the form karmic or jaunty etc.
    """
    if len(sys.argv) < 2:
        logging.error("Usage: %s <listing file>" % sys.argv[0])
        return 1

    input_file = file(sys.argv[1], 'r')
    for package in get_packages(input_file):
        logging.info("Processing package %s" % package.displayname)
        process_package(package)
        print get_upload_aliases(package)


if __name__ == '__main__':
    main()
