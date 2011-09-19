# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""SyncSource facilities tests."""

__metaclass__ = type

import os
import shutil
import subprocess
import sys
import tempfile

from debian.deb822 import (
    Changes,
    Deb822Dict,
    Dsc,
    )
import transaction
from zope.component import getUtility

from canonical.config import config
from canonical.librarian.testing.server import fillLibrarianFile
from canonical.testing.layers import (
    LaunchpadZopelessLayer,
    LibrarianLayer,
    )
from lp.archiveuploader.tagfiles import parse_tagfile
from lp.registry.interfaces.distribution import IDistributionSet
from lp.services.log.logger import BufferLogger
from lp.soyuz.scripts.ftpmaster import (
    generate_changes,
    SyncSource,
    SyncSourceError,
    )
from lp.testing import (
    TestCase,
    TestCaseWithFactory,
    )


class TestSyncSource(TestCaseWithFactory):
    layer = LaunchpadZopelessLayer
    dbuser = 'ro'

    def setUp(self):
        """Create contents in disk for librarian sampledata.

        Setup and chdir into a temp directory, a jail, where we can
        control the file creation properly
        """
        super(TestSyncSource, self).setUp()
        fillLibrarianFile(1, content='one')
        fillLibrarianFile(2, content='two')
        fillLibrarianFile(54, content='fifty-four')
        self._home = os.path.abspath('')
        self._jail = tempfile.mkdtemp()
        os.chdir(self._jail)
        self.logger = BufferLogger()
        self.downloads = []

    def tearDown(self):
        """Remove test contents from disk.

        chdir back to the previous path (home) and remove the temp
        directory used as jail.
        """
        super(TestSyncSource, self).tearDown()
        os.chdir(self._home)
        LibrarianLayer.librarian_fixture.clear()
        shutil.rmtree(self._jail)

    def _listFiles(self):
        """Return a list of files present in jail."""
        return os.listdir(self._jail)

    def get_messages(self):
        """Retrieve the messages sent using the logger."""
        return self.logger.getLogBuffer().splitlines()

    def local_downloader(self, url, filename):
        """Store download requests for future inspections."""
        self.downloads.append((url, filename))
        output = open(filename, 'w')
        output.write('Slartibartfast')
        output.close()

    def _getSyncSource(self, files, origin):
        """Return a SyncSource instance with the given parameters

        Uses the local_* methods to capture results so we can verify
        them later.
        """
        sync_source = SyncSource(
            files=files, origin=origin, logger=self.logger,
            downloader=self.local_downloader,
            todistro=getUtility(IDistributionSet)['ubuntu'])
        return sync_source

    def testInstantiate(self):
        """Check if SyncSource can be instantiated."""
        files = {'foobar': {'size': 1}}
        origin = {'foobar': {'remote-location': 'nowhere'}}

        sync_source = self._getSyncSource(files, origin)

        self.assertEqual(sync_source.files, files)
        self.assertEqual(sync_source.origin, origin)

        sync_source.logger.debug('opa')
        self.assertEqual(self.get_messages(), ['DEBUG opa'])

        sync_source.downloader('somewhere', 'foo')
        self.assertEqual(self.downloads, [('somewhere', 'foo')])
        self.assertEqual(self._listFiles(), ['foo'])
        self.assertEqual(open('foo').read(), 'Slartibartfast')

    def testCheckDownloadedFilesOK(self):
        """Check if checkDownloadFiles really verifies the filesystem

        Pass parameters via 'files' (MD5 & size) that match the file created
        on disk.
        """
        files = {
            'foo': {'md5sum': 'dd21ab16f950f7ac4f9c78ef1498eee1', 'size': 15},
            }
        origin = {}
        sync_source = self._getSyncSource(files, origin)

        test_file = open('foo', 'w')
        test_file.write('abcdefghijlmnop')
        test_file.close()

        sync_source.checkDownloadedFiles()

    def testCheckDownloadedFilesWrongMD5(self):
        """Expect SyncSourceError to be raised due the wrong MD5."""
        files = {
            'foo': {'md5sum': 'duhhhhh', 'size': 15},
            }
        origin = {}
        sync_source = self._getSyncSource(files, origin)

        test_file = open('foo', 'w')
        test_file.write('abcdefghijlmnop')
        test_file.close()

        self.assertRaises(
            SyncSourceError,
            sync_source.checkDownloadedFiles)

    def testCheckDownloadedFilesWrongSize(self):
        """Expect SyncSourceError to be raised due the wrong size."""
        files = {
            'foo': {'md5sum': 'dd21ab16f950f7ac4f9c78ef1498eee1', 'size': 10},
            }
        origin = {}
        sync_source = self._getSyncSource(files, origin)

        test_file = open('foo', 'w')
        test_file.write('abcdefghijlmnop')
        test_file.close()

        self.assertRaises(
            SyncSourceError,
            sync_source.checkDownloadedFiles)

    def testSyncSourceMD5Sum(self):
        """Probe the classmethod provided by SyncSource."""
        test_file = open('foo', 'w')
        test_file.write('abcdefghijlmnop')
        test_file.close()
        md5 = SyncSource.generateMD5Sum('foo')
        self.assertEqual(md5, 'dd21ab16f950f7ac4f9c78ef1498eee1')

    def testFetchSyncFiles(self):
        """Probe fetchSyncFiles.

        It only downloads the files not present in current path, so the
        test_file is skipped.
        """
        files = {
            'foo_0.1.diff.gz': {'remote filename': 'xxx'},
            'foo_0.1.dsc': {'remote filename': 'yyy'},
            'foo_0.1.orig.gz': {'remote filename': 'zzz'},
            }
        origin = {'url': 'http://somewhere/'}

        sync_source = self._getSyncSource(files, origin)

        test_file = open('foo_0.1.diff.gz', 'w')
        test_file.write('nahhh')
        test_file.close()

        dsc_filename = sync_source.fetchSyncFiles()

        self.assertEqual(dsc_filename, 'foo_0.1.dsc')

        self.assertEqual(
            self.downloads,
            [('http://somewhere/zzz', 'foo_0.1.orig.gz'),
             ('http://somewhere/yyy', 'foo_0.1.dsc')])

        for filename in files.keys():
            self.assertTrue(os.path.exists(filename))

    def testFetchLibrarianFilesOK(self):
        """Probe fetchLibrarianFiles.

        Seek on files published from librarian and download matching
        filenames.
        """
        files = {
            'netapplet_1.0.0.orig.tar.gz': {},
            'netapplet_1.0.1.dsc': {},
            'netapplet_1.0.1.diff.gz': {},
            }
        origin = {}
        sync_source = self._getSyncSource(files, origin)

        librarian_files = sync_source.fetchLibrarianFiles()

        self.assertEqual(librarian_files, ['netapplet_1.0.0.orig.tar.gz'])
        self.assertEqual(self._listFiles(), ['netapplet_1.0.0.orig.tar.gz'])
        self.assertEqual(
            self.get_messages(),
            ['INFO netapplet_1.0.0.orig.tar.gz: already in distro '
             '- downloading from librarian'])

    def testFetchLibrarianFilesGotDuplicatedDSC(self):
        """fetchLibrarianFiles fails for an already present version.

        It raises SyncSourceError when it find a DSC or DIFF already
        published, it means that the upload version is duplicated.
        """
        spr = self.factory.makeSourcePackageRelease()
        lfa = self.factory.makeLibraryFileAlias(filename='foobar_1.0.dsc')
        self.factory.makeSourcePackageReleaseFile(
            sourcepackagerelease=spr, library_file=lfa)
        self.factory.makeSourcePackagePublishingHistory(
            archive=getUtility(IDistributionSet)['ubuntu'].main_archive,
            sourcepackagerelease=spr)
        transaction.commit()

        files = {
            'foobar_1.0.orig.tar.gz': {},
            'foobar_1.0.dsc': {},
            'foobar_1.0.diff.gz': {},
            }
        origin = {}
        sync_source = self._getSyncSource(files, origin)

        self.assertRaises(
            SyncSourceError,
            sync_source.fetchLibrarianFiles)

        self.assertEqual(
            self.get_messages(),
            ['INFO foobar_1.0.dsc: already in distro '
             '- downloading from librarian'])
        self.assertEqual(self._listFiles(), ['foobar_1.0.dsc'])


class TestSyncSourceScript(TestCase):
    layer = LaunchpadZopelessLayer
    dbuser = 'ro'

    def setUp(self):
        super(TestSyncSourceScript, self).setUp()
        self._home = os.getcwd()
        self._jail = os.path.join(
            os.path.dirname(__file__), 'sync_source_home')
        os.chdir(self._jail)

    def tearDown(self):
        """'chdir' back to the previous path (home)."""
        super(TestSyncSourceScript, self).tearDown()
        os.chdir(self._home)

    def runSyncSource(self, extra_args=None):
        """Run sync-source.py, returning the result and output.

        Returns a tuple of the process's return code, stdout output and
        stderr output.
        """
        if extra_args is None:
            extra_args = []
        script = os.path.join(
            config.root, "scripts", "ftpmaster-tools", "sync-source.py")
        args = [sys.executable, script]
        args.extend(extra_args)
        process = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        return (process.returncode, stdout, stderr)

    def testSyncSourceRunV1(self):
        """Try a simple sync-source.py run.

        It will run in a special tree prepared to cope with sync-source
        requirements (see `setUp`). It contains a usable archive index
        named as '$distribution_$suite_$component_Sources' and the
        'etherwake' source files.

        Check that:
         * return code is ZERO,
         * check standard error and standard output,
         * check if the expected changesfile was generated,
         * parse and inspect the changesfile using the archiveuploader
           component (the same approach adopted by Soyuz).
         * delete the changesfile.
        """
        returncode, out, err = self.runSyncSource(
            extra_args=['-b', 'cprov', '-D', 'debian', '-C', 'main',
                        '-S', 'incoming', 'bar'])

        self.assertEqual(
            0, returncode, "\nScript Failed:%s\nStdout:\n%s\nStderr\n%s\n"
            % (returncode, out, err))

        self.assertEqual(
            err.splitlines(),
            ['INFO    Creating lockfile: '
             '/var/lock/launchpad-sync-source.lock',
             'W: Could not find blacklist file on '
             '/srv/launchpad.net/dak/sync-blacklist.txt',
             'INFO      - <bar_1.0-1.diff.gz: cached>',
             'INFO      - <bar_1.0.orig.tar.gz: cached>',
             'INFO      - <bar_1.0-1.dsc: cached>',
             ])
        self.assertEqual(
            out.splitlines(),
            ['Getting binaries for hoary...',
             '[Updating] bar (None [Ubuntu] < 1.0-1 [Debian])',
             ' * Trying to add bar...',
             ])

        expected_changesfile = 'bar_1.0-1_source.changes'
        self.assertTrue(
            os.path.exists(expected_changesfile),
            "Couldn't find %s." % expected_changesfile)

        # Parse the generated unsigned changesfile.
        parsed_changes = parse_tagfile(expected_changesfile)

        # It refers to the right source/version.
        self.assertEqual(parsed_changes['Source'], 'bar')
        self.assertEqual(parsed_changes['Version'], '1.0-1')

        # It includes the correct 'origin' and 'target' information.
        self.assertEqual(parsed_changes['Origin'], 'Debian/incoming')
        self.assertEqual(parsed_changes['Distribution'], 'hoary')

        # 'closes' and 'launchpad-bug-fixed' are filled according to
        # what is listed in the debian/changelog.
        self.assertEqual(parsed_changes['Closes'], '1 2 1234 4321')
        self.assertEqual(parsed_changes['Launchpad-bugs-fixed'], '1234 4321')

        # And finally, 'maintainer' role was preserved and 'changed-by'
        # role was assigned as specified in the sync-source command-line.
        self.assertEqual(
            parsed_changes['Maintainer'],
            'Launchpad team <launchpad@lists.canonical.com>')
        self.assertEqual(
            parsed_changes['Changed-By'],
            'Celso Providelo <celso.providelo@canonical.com>')

        os.unlink(expected_changesfile)

    def testSyncSourceRunV3(self):
        """Try a simple sync-source.py run with a version 3 source format
        package.

        It will run in a special tree prepared to cope with sync-source
        requirements (see `setUp`). It contains a usable archive index
        named as '$distribution_$suite_$component_Sources' and the
        'etherwake' source files.

        Check that:
         * return code is ZERO,
         * check standard error and standard output,
         * check if the expected changesfile was generated,
         * parse and inspect the changesfile using the archiveuploader
           component (the same approach adopted by Soyuz).
         * delete the changesfile.
        """
        returncode, out, err = self.runSyncSource(
            extra_args=['-b', 'cprov', '-D', 'debian', '-C', 'main',
                        '-S', 'incoming', 'sample1'])

        self.assertEqual(
            0, returncode, "\nScript Failed:%s\nStdout:\n%s\nStderr\n%s\n"
            % (returncode, out, err))

        self.assertEqual(
            err.splitlines(),
            ['INFO    Creating lockfile: '
             '/var/lock/launchpad-sync-source.lock',
             'W: Could not find blacklist file on '
             '/srv/launchpad.net/dak/sync-blacklist.txt',
             'INFO      - <sample1_1.0.orig-component3.tar.gz: cached>',
             'INFO      - <sample1_1.0-1.dsc: cached>',
             'INFO      - <sample1_1.0-1.debian.tar.gz: cached>',
             'INFO      - <sample1_1.0.orig-component1.tar.bz2: cached>',
             'INFO      - <sample1_1.0.orig-component2.tar.lzma: cached>',
             'INFO      - <sample1_1.0.orig.tar.gz: cached>'])
        self.assertEqual(
            out.splitlines(),
            ['Getting binaries for hoary...',
             '[Updating] sample1 (None [Ubuntu] < 1.0-1 [Debian])',
             ' * Trying to add sample1...',
             ])

        expected_changesfile = 'sample1_1.0-1_source.changes'
        self.assertTrue(
            os.path.exists(expected_changesfile),
            "Couldn't find %s." % expected_changesfile)

        # Parse the generated unsigned changesfile.
        parsed_changes = parse_tagfile(expected_changesfile)

        # It refers to the right source/version.
        self.assertEqual(parsed_changes['Source'], 'sample1')
        self.assertEqual(parsed_changes['Version'], '1.0-1')

        # It includes the correct 'origin' and 'target' information.
        self.assertEqual(parsed_changes['Origin'], 'Debian/incoming')
        self.assertEqual(parsed_changes['Distribution'], 'hoary')

        # And finally, 'maintainer' role was preserved and 'changed-by'
        # role was assigned as specified in the sync-source command-line.
        self.assertEqual(
            parsed_changes['Maintainer'],
            'Raphael Hertzog <hertzog@debian.org>')
        self.assertEqual(
            parsed_changes['Changed-By'],
            'Celso Providelo <celso.providelo@canonical.com>')

        os.unlink(expected_changesfile)


class TestGenerateChanges(TestCase):
    """Test generate_changes()."""

    def getBaseDsc(self):
        """Create a basic Dsc object for use with generate_changes()."""
        dsc = Dsc()
        dsc["source"] = "mysrcpkg"
        dsc["binary"] = "mybinpkg"
        dsc["version"] = "4.2"
        dsc["maintainer"] = "Maintainer <maintainer@ubuntu.com>"
        return dsc

    def getBaseOrigin(self):
        """Create a basic Origin dict for use with generate_changes()."""
        origin = Deb822Dict()
        origin["Name"] = "Debian"
        origin["Suite"] = "sid"
        return origin

    def generateChanges(self, dsc=None, dsc_files=None, suite="maverick",
                        changelog=None, urgency="low", closes=None,
                        lp_closes=None, section="net", priority="extra",
                        description=None, files_from_librarian=[],
                        requested_by="Somebody <somebody@ubuntu.com>",
                        origin=None):
        if dsc is None:
            dsc = self.getBaseDsc()
        if dsc_files is None:
            dsc_files = []
        if origin is None:
            origin = self.getBaseOrigin()
        if changelog is None:
            changelog = 'changelog entry'
        return generate_changes(
            dsc=dsc, dsc_files=dsc_files, suite=suite, changelog=changelog,
            urgency=urgency, closes=closes, lp_closes=lp_closes,
            section=section, priority=priority, description=description,
            files_from_librarian=files_from_librarian,
            requested_by=requested_by, origin=origin)

    def test_minimum_fields(self):
        # The right (minimum) set of fields are set by generate_changes().
        changes = self.generateChanges()
        self.assertEquals("1.7", changes["Format"])
        self.assertEquals("mysrcpkg", changes["Source"])
        self.assertEquals("mybinpkg", changes["Binary"])
        self.assertEquals("source", changes["Architecture"])
        self.assertEquals("4.2", changes["Version"])
        self.assertEquals("maverick", changes["Distribution"])
        self.assertEquals("low", changes["Urgency"])
        self.assertEquals("\nchangelog entry", changes["Changes"])
        self.assertEquals(
            "Maintainer <maintainer@ubuntu.com>", changes["Maintainer"])
        self.assertNotIn("Description", changes)
        self.assertNotIn("Closes", changes)
        self.assertNotIn("Launchpad-bugs-fixed", changes)
        self.assertEquals([], changes["Files"])

    def test_closes(self):
        # Closes gets set if any Debian bugs to close were specified.
        changes = self.generateChanges(closes=["1232", "4323"])
        self.assertEquals("1232 4323", changes["Closes"])
        self.assertNotIn("Launchpad-bugs-fixed", changes)

    def test_binary_newline(self):
        # If the Dsc Binary: line contains newlines those are properly
        # formatted in the new changes file.
        dsc = self.getBaseDsc()
        dsc["Binary"] = "binary1\n binary2 \n binary3"
        changes = self.generateChanges(dsc=dsc)
        self.assertEquals("binary1\n binary2 \n binary3", changes["Binary"])

    def test_lp_closes(self):
        # Launchpad-Bugs-Fixed gets set if any Launchpad bugs to close were
        # specified.
        changes = self.generateChanges(lp_closes=["987987"])
        self.assertEquals("987987", changes["Launchpad-Bugs-Fixed"])

    def test_utf8_changelog(self):
        # A changelog entry with non-ASCII UTF-8 characters is serialized in
        # Changes properly.
        changes = self.generateChanges(
            changelog="* Updated French translation by J\xc3\xa9lmer.")
        contents = changes.dump(encoding="utf-8").encode("utf-8")
        self.assertIn(
            "Updated French translation by J\xc3\xa9lmer.", contents)

    def test_changelog_whitelines(self):
        # The changelog entry can contain empty lines, and this should not
        # mess up the parsing of the changes file.
        changelog = "* Foo\n\n\n* Bar\n.\nEntries"
        changes = self.generateChanges(changelog=changelog)
        contents = changes.dump(encoding="utf-8").encode("utf-8")
        # Read contents back
        read_changes = Changes(contents)
        self.assertEquals("\n%s" % changelog, changes['Changes'])
        self.assertContentEqual([
            'Architecture',
            'Binary',
            'Changed-By',
            'Changes',
            'Date',
            'Distribution',
            'Files',
            'Format',
            'Maintainer',
            'Origin',
            'Source',
            'Urgency',
            'Version',
            ], read_changes.keys())
