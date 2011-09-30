#!/usr/bin/python -S
#
# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# <james.troup@canonical.com>
# pylint: disable-msg=W0403

""" 'Sync' a source package by generating an upload.

This is a straight port of the original dak 'josie' tool to soyuz.

Long term once soyuz is monitoring other archives regularly, syncing
will become a matter of simply 'publishing' source from Debian unstable
wherever) into Ubuntu dapper and the whole fake upload trick can go away.
"""

import errno
import os
import re
import shutil
import stat
import string
import tempfile
import urllib

import _pythonpath
from _syncorigins import origins
import apt_pkg
import dak_utils
from debian.deb822 import Dsc
from zope.component import getUtility

from canonical.database.sqlbase import (
    cursor,
    sqlvalues,
    )
from canonical.librarian.client import LibrarianClient
from lp.archiveuploader.utils import (
    DpkgSourceError,
    extract_dpkg_source,
    )
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.pocket import PackagePublishingPocket
from lp.services.scripts.base import (
    LaunchpadScript,
    LaunchpadScriptFailure,
    )
from lp.soyuz.enums import (
    PackagePublishingStatus,
    re_bug_numbers,
    re_closes,
    re_lp_closes,
    )
from lp.soyuz.scripts.ftpmaster import (
    generate_changes,
    SyncSource,
    SyncSourceError,
    )


reject_message = ""
re_strip_revision = re.compile(r"-([^-]+)$")
re_changelog_header = re.compile(
    r"^\S+ \((?P<version>.*)\) .*;.*urgency=(?P<urgency>\w+).*")


Blacklisted = None
Library = None
Log = None
Options = None


def md5sum_file(filename):
    file_handle = open(filename)
    md5sum = apt_pkg.md5sum(file_handle)
    file_handle.close()
    return md5sum


def reject(str, prefix="Rejected: "):
    global reject_message
    if str:
        reject_message += prefix + str + "\n"


# Following two functions are borrowed and (modified) from apt-listchanges
def urgency_to_numeric(u):
    urgency_map = {
        'low': 1,
        'medium': 2,
        'high': 3,
        'emergency': 4,
        'critical': 4,
        }
    return urgency_map.get(u.lower(), 1)


def urgency_from_numeric(n):
    urgency_map = {
        1: 'low',
        2: 'medium',
        3: 'high',
        4: 'critical',
        }
    return urgency_map.get(n, 'low')


def parse_changelog(changelog_filename, previous_version):
    if not os.path.exists(changelog_filename):
        raise LaunchpadScriptFailure(
            "debian/changelog not found in extracted source.")
    urgency = urgency_to_numeric('low')
    changes = ""
    is_debian_changelog = 0
    changelog_file = open(changelog_filename)
    for line in changelog_file.readlines():
        match = re_changelog_header.match(line)
        if match:
            is_debian_changelog = 1
            if previous_version is None:
                previous_version = "9999:9999"
            elif apt_pkg.VersionCompare(
                match.group('version'), previous_version) > 0:
                urgency = max(
                    urgency_to_numeric(match.group('urgency')), urgency)
            else:
                break
        changes += line

    if not is_debian_changelog:
        raise LaunchpadScriptFailure("header not found in debian/changelog")

    closes = []
    for match in re_closes.finditer(changes):
        bug_match = re_bug_numbers.findall(match.group(0))
        closes += map(int, bug_match)

    l = map(int, closes)
    l.sort()
    closes = map(str, l)

    lp_closes = []
    for match in re_lp_closes.finditer(changes):
        bug_match = re_bug_numbers.findall(match.group(0))
        lp_closes += map(int, bug_match)

    l = map(int, lp_closes)
    l.sort()
    lp_closes = map(str, l)

    return (changes, urgency_from_numeric(urgency), closes, lp_closes)


def fix_changelog(changelog):
    """Fix debian/changelog entries to be in .changes compatible format."""
    fixed = []
    fixed_idx = -1
    for line in changelog.split("\n"):
        if line == "":
            fixed += [" ."]
            fixed_idx += 1
        elif line.startswith(" --"):
            # Strip any 'blank' lines preceeding the footer
            while fixed[fixed_idx] == " .":
                fixed.pop()
                fixed_idx -= 1
        else:
            fixed += [" %s" % (line)]
            fixed_idx += 1
    # Strip trailing 'blank' lines
    while fixed[fixed_idx] == " .":
        fixed.pop()
        fixed_idx -= 1
    fixed_changelog = "\n".join(fixed)
    fixed_changelog += "\n"
    return fixed_changelog


def parse_control(control_filename):
    """Parse a debian/control file.

    Extract section, priority and description if possible.
    """
    source_name = ""
    source_section = "-"
    source_priority = "-"
    source_description = ""

    if not os.path.exists(control_filename):
        raise LaunchpadScriptFailure(
            "debian/control not found in extracted source.")
    control_filehandle = open(control_filename)
    Control = apt_pkg.ParseTagFile(control_filehandle)
    while Control.Step():
        source = Control.Section.Find("Source")
        package = Control.Section.Find("Package")
        section = Control.Section.Find("Section")
        priority = Control.Section.Find("Priority")
        description = Control.Section.Find("Description")
        if source is not None:
            if section is not None:
                source_section = section
            if priority is not None:
                source_priority = priority
            source_name = source
        if package is not None and package == source_name:
            source_description = (
                "%-10s - %-.65s" % (package, description.split("\n")[0]))
    control_filehandle.close()

    return (source_section, source_priority, source_description)


def extract_source(dsc_filename):
    # Create and move into a temporary directory
    tmpdir = tempfile.mkdtemp()
    old_cwd = os.getcwd()

    # Extract the source package
    try:
        extract_dpkg_source(dsc_filename, tmpdir)
    except DpkgSourceError, e:
        print " * command was '%s'" % (e.command)
        print e.output
        raise LaunchpadScriptFailure(
            "'dpkg-source -x' failed for %s [return code: %s]." %
            (dsc_filename, e.result))

    os.chdir(tmpdir)
    return (old_cwd, tmpdir)


def cleanup_source(tmpdir, old_cwd, dsc):
    # Sanity check that'll probably break if people set $TMPDIR, but
    # WTH, shutil.rmtree scares me
    if not tmpdir.startswith("/tmp/"):
        raise LaunchpadScriptFailure(
            "%s: tmpdir doesn't start with /tmp" % (tmpdir))

    # Move back and cleanup the temporary tree
    os.chdir(old_cwd)
    try:
        shutil.rmtree(tmpdir)
    except OSError, e:
        if errno.errorcode[e.errno] != 'EACCES':
            raise LaunchpadScriptFailure(
                "%s: couldn't remove tmp dir for source tree."
                % (dsc["source"]))

        reject("%s: source tree could not be cleanly removed."
               % (dsc["source"]))
        # We probably have u-r or u-w directories so chmod everything
        # and try again.
        cmd = "chmod -R u+rwx %s" % (tmpdir)
        result = os.system(cmd)
        if result != 0:
            raise LaunchpadScriptFailure(
                "'%s' failed with result %s." % (cmd, result))
        shutil.rmtree(tmpdir)
    except:
        raise LaunchpadScriptFailure(
            "%s: couldn't remove tmp dir for source tree." % (dsc["source"]))


def check_dsc(dsc, current_sources, current_binaries):
    source = dsc["source"]
    if source in current_sources:
        source_component = current_sources[source][1]
    else:
        source_component = "universe"
    for binary in map(string.strip, dsc["binary"].split(',')):
        if binary in current_binaries:
            (current_version, current_component) = current_binaries[binary]

            # Check that a non-main source package is not trying to
            # override a main binary package
            if current_component == "main" and source_component != "main":
                if not Options.forcemore:
                    raise LaunchpadScriptFailure(
                        "%s is in main but its source (%s) is not." %
                        (binary, source))
                else:
                    Log.warning(
                        "%s is in main but its source (%s) is not - "
                        "continuing anyway." % (binary, source))

            # Check that a source package is not trying to override an
            # ubuntu-modified binary package
            ubuntu_bin = current_binaries[binary][0].find("ubuntu")
            if not Options.force and ubuntu_bin != -1:
                raise LaunchpadScriptFailure(
                    "%s is trying to override %s_%s without -f/--force." %
                    (source, binary, current_version))
            print "I: %s [%s] -> %s_%s [%s]." % (
                source, source_component, binary, current_version,
                current_component)


def import_dsc(dsc_filename, suite, previous_version, signing_rules,
               files_from_librarian, requested_by, origin, current_sources,
               current_binaries):
    dsc_file = open(dsc_filename, 'r')
    dsc = Dsc(dsc_file)

    if signing_rules.startswith("must be signed"):
        dsc_file.seek(0)
        (gpg_pre, payload, gpg_post) = Dsc.split_gpg_and_payload(dsc_file)
        if gpg_pre == [] and gpg_post == []:
            raise LaunchpadScriptFailure(
                "signature required for %s but not present" % dsc_filename)
        if signing_rules == "must be signed and valid":
            if (gpg_pre[0] != "-----BEGIN PGP SIGNED MESSAGE-----" or
                gpg_post[0] != "-----BEGIN PGP SIGNATURE-----"):
                raise LaunchpadScriptFailure(
                    "signature for %s invalid %r %r" %
                    (dsc_filename, gpg_pre, gpg_post))

    dsc_files = dict((entry['name'], entry) for entry in dsc['files'])
    check_dsc(dsc, current_sources, current_binaries)

    # Add the .dsc itself to dsc_files so it's listed in the Files: field
    dsc_base_filename = os.path.basename(dsc_filename)
    dsc_files.setdefault(dsc_base_filename, {})
    dsc_files[dsc_base_filename]["md5sum"] = md5sum_file(dsc_filename)
    dsc_files[dsc_base_filename]["size"] = os.stat(dsc_filename)[stat.ST_SIZE]

    (old_cwd, tmpdir) = extract_source(dsc_filename)

    # Get the upstream version
    upstr_version = dak_utils.re_no_epoch.sub('', dsc["version"])
    if re_strip_revision.search(upstr_version):
        upstr_version = re_strip_revision.sub('', upstr_version)

    # Ensure the changelog file exists
    changelog_filename = (
        "%s-%s/debian/changelog" % (dsc["source"], upstr_version))

    # Parse it and then adapt it for .changes
    (changelog, urgency, closes, lp_closes) = parse_changelog(
        changelog_filename, previous_version)
    changelog = fix_changelog(changelog)

    # Parse the control file
    control_filename = "%s-%s/debian/control" % (dsc["source"], upstr_version)
    (section, priority, description) = parse_control(control_filename)

    cleanup_source(tmpdir, old_cwd, dsc)

    changes = generate_changes(
        dsc, dsc_files, suite, changelog, urgency, closes, lp_closes,
        section, priority, description, files_from_librarian, requested_by,
        origin)

    output_filename = "%s_%s_source.changes" % (
        dsc["source"], dak_utils.re_no_epoch.sub('', dsc["version"]))

    filehandle = open(output_filename, 'w')
    try:
        changes.dump(filehandle, encoding="utf-8")
    finally:
        filehandle.close()


def read_current_source(distro_series, valid_component=None, arguments=None):
    """Returns a dictionary of packages in 'suite'.

    The dictionary contains their version as the attribute.
    'component' is an optional list of (comma or whitespace separated)
    components to restrict the search to.
    """
    S = {}

    # XXX cprov 2007-07-10: This searches all pockets of the
    #     distro_series which is not what we want.
    if Options.all:
        spp = distro_series.getSourcePackagePublishing(
            status=PackagePublishingStatus.PUBLISHED,
            pocket=PackagePublishingPocket.RELEASE)
    else:
        spp = []
        for package in arguments:
            spp.extend(distro_series.getPublishedSources(package))

    for sp in spp:
        component = sp.component.name
        version = sp.sourcepackagerelease.version
        pkg = sp.sourcepackagerelease.sourcepackagename.name

        if (valid_component is not None and
            component != valid_component.name):
            Log.warning(
                "%s/%s: skipping because it is not in %s component" % (
                pkg, version, component))
            continue

        if pkg not in S:
            S[pkg] = [version, component]
        else:
            if apt_pkg.VersionCompare(S[pkg][0], version) < 0:
                Log.warning(
                    "%s: skipping because %s is < %s" % (
                    pkg, version, S[pkg][0]))
                S[pkg] = [version, component]
    return S


def read_current_binaries(distro_series):
    """Returns a dictionary of binaries packages in 'distro_series'.

    The dictionary contains their version and component as the attributes.
    """
    B = {}

    # XXX cprov 2007-07-10: This searches all pockets of the
    #     distro_series which is not what we want.

    # XXX James Troup 2006-02-03: this is insanely slow due to how It
    #     SQLObject works. Can be limited, but only if we know what
    #     binaries we want to check against, which we don't know till
    #     we have the .dsc file and currently this function is
    #     run well before that.
    #
    #     for distroarchseries in distro_series.architectures:
    #         bpp = distroarchseries.getAllReleasesByStatus(
    #             PackagePublishingStatus.PUBLISHED)
    #
    #         for bp in bpp:
    #             component = bp.component.name
    #             version = bp.binarypackagerelease.version
    #             pkg = bp.binarypackagerelease.binarypackagename.name
    #
    #             if pkg not in B:
    #                 B[pkg] = [version, component]
    #             else:
    #                 if apt_pkg.VersionCompare(B[pkg][0], version) < 0:
    #                     B[pkg] = [version, component]

    # XXX James Troup 2006-02-22: so... let's fall back on raw SQL
    das_ids = [das.id for das in distro_series.architectures]
    archive_ids = [a.id for a in Options.todistro.all_distro_archives]
    cur = cursor()
    query = """
    SELECT bpn.name, bpr.version, c.name
    FROM binarypackagerelease bpr, binarypackagename bpn, component c,
        binarypackagepublishinghistory sbpph, distroarchseries dar
    WHERE
        bpr.binarypackagename = bpn.id AND
             sbpph.binarypackagerelease = bpr.id AND
        sbpph.component = c.id AND
        sbpph.distroarchseries = dar.id AND
        sbpph.status = %s AND
        sbpph.archive IN %s AND
        dar.id IN %s
     """ % sqlvalues(
        PackagePublishingStatus.PUBLISHED, archive_ids, das_ids)
    cur.execute(query)

    print "Getting binaries for %s..." % (distro_series.name)
    for (pkg, version, component) in cur.fetchall():
        if pkg not in B:
            B[pkg] = [version, component]
        else:
            if apt_pkg.VersionCompare(B[pkg][0], version) < 0:
                B[pkg] = [version, component]
    return B


def read_Sources(filename, origin):
    S = {}

    suite = origin["suite"]
    component = origin["component"]
    if suite:
        suite = "_%s" % (suite)
    if component:
        component = "_%s" % (component)

    filename = "%s%s%s_%s" % (origin["name"], suite, component, filename)
    sources_filehandle = open(filename)
    Sources = apt_pkg.ParseTagFile(sources_filehandle)
    while Sources.Step():
        pkg = Sources.Section.Find("Package")
        version = Sources.Section.Find("Version")

        if pkg in S and apt_pkg.VersionCompare(
            S[pkg]["version"], version) > 0:
            continue

        S[pkg] = {}
        S[pkg]["version"] = version

        directory = Sources.Section.Find("Directory", "")
        files = {}
        for line in Sources.Section.Find("Files").split('\n'):
            (md5sum, size, filename) = line.strip().split()
            files[filename] = {}
            files[filename]["md5sum"] = md5sum
            files[filename]["size"] = int(size)
            files[filename]["remote filename"] = (
                os.path.join(directory, filename))
        S[pkg]["files"] = files
    sources_filehandle.close()
    return S


def add_source(pkg, Sources, previous_version, suite, requested_by, origin,
               current_sources, current_binaries):
    print " * Trying to add %s..." % (pkg)

    # Check it's in the Sources file
    if pkg not in Sources:
        raise LaunchpadScriptFailure(
            "%s doesn't exist in the Sources file." % (pkg))

    syncsource = SyncSource(Sources[pkg]["files"], origin, Log,
        urllib.urlretrieve, Options.todistro)
    try:
        files_from_librarian = syncsource.fetchLibrarianFiles()
        dsc_filename = syncsource.fetchSyncFiles()
        syncsource.checkDownloadedFiles()
    except SyncSourceError, e:
        raise LaunchpadScriptFailure("Fetching files failed: %s" % (str(e),))

    if dsc_filename is None:
        raise LaunchpadScriptFailure(
            "No dsc filename in %r" % Sources[pkg]["files"].keys())

    import_dsc(os.path.abspath(dsc_filename), suite, previous_version,
               origin["dsc"], files_from_librarian, requested_by, origin,
               current_sources, current_binaries)


class Percentages:
    """Helper to compute percentage ratios compared to a fixed total."""

    def __init__(self, total):
        self.total = total

    def get_ratio(self, number):
        """Report the ration of `number` to `self.total`, as a percentage."""
        return (float(number) / self.total) * 100


def do_diff(Sources, Suite, origin, arguments, current_binaries):
    stat_us = 0
    stat_cant_update = 0
    stat_updated = 0
    stat_uptodate_modified = 0
    stat_uptodate = 0
    stat_count = 0
    stat_broken = 0
    stat_blacklisted = 0

    if Options.all:
        packages = Suite.keys()
    else:
        packages = arguments
    packages.sort()
    for pkg in packages:
        stat_count += 1
        dest_version = Suite.get(pkg, [None, ""])[0]

        if pkg not in Sources:
            if not Options.all:
                raise LaunchpadScriptFailure("%s: not found" % (pkg))
            else:
                print "[Ubuntu Specific] %s_%s" % (pkg, dest_version)
                stat_us += 1
                continue

        if pkg in Blacklisted:
            print "[BLACKLISTED] %s_%s" % (pkg, dest_version)
            stat_blacklisted += 1
            continue

        source_version = Sources[pkg]["version"]
        if (dest_version is None
                or apt_pkg.VersionCompare(dest_version, source_version) < 0):
            if (dest_version is not None
                    and (not Options.force
                        and dest_version.find("ubuntu") != -1)):
                stat_cant_update += 1
                print ("[NOT Updating - Modified] %s_%s (vs %s)"
                       % (pkg, dest_version, source_version))
            else:
                stat_updated += 1
                print ("[Updating] %s (%s [Ubuntu] < %s [%s])"
                       % (pkg, dest_version, source_version, origin["name"]))
                if Options.action:
                    add_source(
                        pkg, Sources,
                        Suite.get(pkg, ["0", ""])[0], Options.tosuite.name,
                        Options.requestor, origin, Suite, current_binaries)
        else:
            if dest_version.find("ubuntu") != -1:
                stat_uptodate_modified += 1
                if Options.moreverbose or not Options.all:
                    print ("[Nothing to update (Modified)] %s_%s (vs %s)"
                           % (pkg, dest_version, source_version))
            else:
                stat_uptodate += 1
                if Options.moreverbose or not Options.all:
                    print (
                        "[Nothing to update] %s (%s [ubuntu] >= %s [debian])"
                        % (pkg, dest_version, source_version))

    if Options.all:
        percentages = Percentages(stat_count)
        print
        print ("Out-of-date BUT modified: %3d (%.2f%%)"
            % (stat_cant_update, percentages.get_ratio(stat_cant_update)))
        print ("Updated:                  %3d (%.2f%%)"
            % (stat_updated, percentages.get_ratio(stat_updated)))
        print ("Ubuntu Specific:          %3d (%.2f%%)"
            % (stat_us, percentages.get_ratio(stat_us)))
        print ("Up-to-date [Modified]:    %3d (%.2f%%)"
            % (stat_uptodate_modified, percentages.get_ratio(
                stat_uptodate_modified)))
        print ("Up-to-date:               %3d (%.2f%%)"
               % (stat_uptodate, percentages.get_ratio(stat_uptodate)))
        print ("Blacklisted:              %3d (%.2f%%)"
               % (stat_blacklisted, percentages.get_ratio(stat_blacklisted)))
        print ("Broken:                   %3d (%.2f%%)"
               % (stat_broken, percentages.get_ratio(stat_broken)))
        print "                          -----------"
        print "Total:                    %s" % (stat_count)


def objectize_options():
    """Parse given options.

    Convert 'target_distro', 'target_suite' and 'target_component' to objects
    rather than strings.
    """
    Options.todistro = getUtility(IDistributionSet)[Options.todistro]

    if not Options.tosuite:
        Options.tosuite = Options.todistro.currentseries.name
    Options.tosuite = Options.todistro.getSeries(Options.tosuite)

    valid_components = (
        dict([(component.name, component)
              for component in Options.tosuite.components]))

    if Options.tocomponent is not None:

        if Options.tocomponent not in valid_components:
            raise LaunchpadScriptFailure(
                "%s is not a valid component for %s/%s."
                % (Options.tocomponent, Options.todistro.name,
                   Options.tosuite.name))

        Options.tocomponent = valid_components[Options.tocomponent]

    # Fix up Options.requestor
    if not Options.requestor:
        Options.requestor = "katie"

    PersonSet = getUtility(IPersonSet)
    person = PersonSet.getByName(Options.requestor)
    if not person:
        raise LaunchpadScriptFailure(
            "Unknown LaunchPad user id '%s'." % (Options.requestor))
    Options.requestor = "%s <%s>" % (person.displayname,
                                     person.preferredemail.email)
    Options.requestor = Options.requestor.encode("ascii", "replace")


def parseBlacklist(path):
    """Parse given file path as a 'blacklist'.

    Format:

    {{{
    # [comment]
    <sourcename> # [comment]
    }}}

    Return a blacklist dictionary where the keys are blacklisted source
    package names.

    Return an empty dictionary if the given 'path' doesn't exist.
    """
    blacklist = {}

    try:
        blacklist_file = open(path)
    except IOError:
        Log.warning('Could not find blacklist file on %s' % path)
        return blacklist

    for line in blacklist_file:
        try:
            line = line[:line.index("#")]
        except ValueError:
            pass
        line = line.strip()
        if not line:
            continue
        blacklist[line] = ""
    blacklist_file.close()

    return blacklist


class SyncSourceScript(LaunchpadScript):

    def add_my_options(self):
        self.parser.add_option("-a", "--all", dest="all",
                        default=False, action="store_true",
                        help="sync all packages")
        self.parser.add_option("-b", "--requested-by", dest="requestor",
                        help="who the sync was requested by")
        self.parser.add_option("-f", "--force", dest="force",
                        default=False, action="store_true",
                        help="force sync over the top of Ubuntu changes")
        self.parser.add_option("-F", "--force-more", dest="forcemore",
                        default=False, action="store_true",
                        help="force sync even when components don't match")
        self.parser.add_option("-n", "--noaction", dest="action",
                        default=True, action="store_false",
                        help="don't do anything")

        # Options controlling where to sync packages to:
        self.parser.add_option("-c", "--to-component", dest="tocomponent",
                        help="limit syncs to packages in COMPONENT")
        self.parser.add_option("-d", "--to-distro", dest="todistro",
                        default='ubuntu', help="sync to DISTRO")
        self.parser.add_option("-s", "--to-suite", dest="tosuite",
                        help="sync to SUITE (aka distroseries)")

        # Options controlling where to sync packages from:
        self.parser.add_option("-C", "--from-component", dest="fromcomponent",
                        help="sync from COMPONENT")
        self.parser.add_option("-D", "--from-distro", dest="fromdistro",
                        default='debian', help="sync from DISTRO")
        self.parser.add_option("-S", "--from-suite", dest="fromsuite",
                        help="sync from SUITE (aka distroseries)")
        self.parser.add_option("-B", "--blacklist", dest="blacklist_path",
                        default="/srv/launchpad.net/dak/sync-blacklist.txt",
                        help="Blacklist file path.")

    def main(self):
        global Blacklisted, Library, Log, Options

        Log = self.logger
        Options = self.options

        distro = Options.fromdistro.lower()
        if not Options.fromcomponent:
            Options.fromcomponent = origins[distro]["default component"]
        if not Options.fromsuite:
            Options.fromsuite = origins[distro]["default suite"]

        # Sanity checks on options
        if not Options.all and not self.args:
            raise LaunchpadScriptFailure(
                "Need -a/--all or at least one package name as an argument.")

        apt_pkg.init()
        Library = LibrarianClient()

        objectize_options()

        Blacklisted = parseBlacklist(Options.blacklist_path)

        origin = origins[Options.fromdistro]
        origin["suite"] = Options.fromsuite
        origin["component"] = Options.fromcomponent

        Sources = read_Sources("Sources", origin)
        Suite = read_current_source(
            Options.tosuite, Options.tocomponent, self.args)
        current_binaries = read_current_binaries(Options.tosuite)
        do_diff(Sources, Suite, origin, self.args, current_binaries)


if __name__ == '__main__':
    SyncSourceScript('sync-source', 'ro').lock_and_run()
