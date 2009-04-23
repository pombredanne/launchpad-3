# Copyright 2009 Canonical Ltd.  All rights reserved.

from datetime import datetime
import gzip
import os
from StringIO import StringIO
import subprocess
import tempfile
import unittest

from zope.component import getUtility

from canonical.launchpad.database.librarian import ParsedApacheLog
from canonical.launchpad.interfaces.librarian import ILibraryFileAliasSet
from canonical.launchpad.scripts.librarian_apache_log_parser import (
    create_or_update_parsedlog_entry, DBUSER,
    get_host_date_status_and_request, get_day, get_files_to_parse,
    get_method_and_file_id, parse_file)
from canonical.launchpad.ftests import ANONYMOUS, login
from canonical.launchpad.testing import TestCase
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)
from canonical.testing import (
    DatabaseFunctionalLayer, LaunchpadZopelessLayer, ZopelessLayer)


here = os.path.dirname(__file__)


class TestLineParsing(TestCase):
    """Test parsing of lines of an apache log file."""

    def test_return_value(self):
        fd = open(
            os.path.join(here, 'apache-log-files', 'librarian-oneline.log'))
        host, date, status, request = get_host_date_status_and_request(
            fd.readline())
        self.assertEqual(host, '201.158.154.121')
        self.assertEqual(date, '[13/Jun/2008:18:38:57 +0100]')
        self.assertEqual(status, '200')
        self.assertEqual(
            request, 'GET /15166065/gnome-do-0.5.0.1.tar.gz HTTP/1.1')

    def test_day_extraction(self):
        date = '[13/Jun/2008:18:38:57 +0100]'
        self.assertEqual(get_day(date), datetime(2008, 6, 13))


class TestRequestParsing(TestCase):
    """Test parsing the request part of an apache log line."""

    def assertMethodAndFileIDAreCorrect(self, request):
        method, file_id = get_method_and_file_id(request)
        self.assertEqual(method, 'GET')
        self.assertEqual(file_id, '8196569')

    def test_return_value(self):
        request = 'GET /8196569/mediumubuntulogo.png HTTP/1.1'
        self.assertMethodAndFileIDAreCorrect(request)

    def test_return_value_for_http_path(self):
        request = ('GET http://launchpadlibrarian.net/8196569/'
                   'mediumubuntulogo.png HTTP/1.1')
        self.assertMethodAndFileIDAreCorrect(request)

    def test_return_value_for_https_path(self):
        request = ('GET https://launchpadlibrarian.net/8196569/'
                   'mediumubuntulogo.png HTTP/1.1')
        self.assertMethodAndFileIDAreCorrect(request)


class TestLogFileParsing(TestCase):
    """Test the parsing of log files."""

    layer = ZopelessLayer
    sample_line = (
        '69.233.136.42 - - [13/Jun/2008:14:55:22 +0100] "%(method)s '
        '/15018215/ul_logo_64x64.png HTTP/1.1" %(status)s 2261 '
        '"https://launchpad.net/~ubuntulite/+archive" "Mozilla/5.0 (X11; '
        'U; Linux i686; en-US; rv:1.9b5) Gecko/2008041514 Firefox/3.0b5"')

    def _getLastLineStart(self, fd):
        """Return the position (in bytes) where the last line of the given
        file starts.
        """
        fd.seek(0)
        lines = fd.readlines()
        return fd.tell() - len(lines[-1])

    def test_parsing(self):
        # The parse_file() function returns a tuple containing a dict (mapping
        # days and library file IDs to number of downloads) and the total
        # number of bytes that have been parsed from this file.  In our sample
        # log, the file with ID 8196569 has been downloaded twice (once from
        # Argentina and once from Japan) and the files with ID 12060796
        # and 9096290 have been downloaded once.  The file with ID 15018215
        # has also been downloaded once (last line of the sample log), but
        # parse_file() always skips the last line as it may be truncated, so
        # it doesn't show up in the dict returned.
        fd = open(os.path.join(
            here, 'apache-log-files', 'launchpadlibrarian.net.access-log'))
        downloads, parsed_bytes = parse_file(fd, start_position=0)
        date = datetime(2008, 6, 13)
        self.assertContentEqual(
            downloads.items(),
            [('8196569', {date: {'AR': 1, 'JP': 1}}),
             ('9096290', {date: {'AU': 1}}),
             ('12060796', {date: {'AU': 1}})])

        # The last line is skipped, so we'll record that the file has been
        # parsed until the beginning of the last line.
        self.assertNotEqual(parsed_bytes, fd.tell())
        self.assertEqual(parsed_bytes, self._getLastLineStart(fd))

    def test_parsing_last_line(self):
        # When there's only the last line of a given file for us to parse, we
        # assume the file has been rotated and it's safe to parse its last
        # line without worrying about whether or not it's been truncated.
        fd = open(os.path.join(
            here, 'apache-log-files', 'launchpadlibrarian.net.access-log'))
        downloads, parsed_bytes = parse_file(
            fd, start_position=self._getLastLineStart(fd))
        self.assertEqual(parsed_bytes, fd.tell())

        self.assertContentEqual(
            downloads.items(),
            [('15018215', {datetime(2008, 6, 13): {'US': 1}})])

    def _assertResponseWithGivenStatusIsIgnored(self, status):
        """Assert that responses with the given status are ignored."""
        fd = StringIO(
            self.sample_line % dict(status=status, method='GET'))
        downloads, parsed_bytes = parse_file(fd, start_position=0)
        self.assertEqual(downloads, {})
        self.assertEqual(parsed_bytes, fd.tell())

    def test_responses_with_404_status_are_ignored(self):
        self._assertResponseWithGivenStatusIsIgnored('404')

    def test_responses_with_206_status_are_ignored(self):
        self._assertResponseWithGivenStatusIsIgnored('206')

    def test_responses_with_304_status_are_ignored(self):
        self._assertResponseWithGivenStatusIsIgnored('304')

    def test_responses_with_503_status_are_ignored(self):
        self._assertResponseWithGivenStatusIsIgnored('503')

    def _assertRequestWithGivenMethodIsIgnored(self, method):
        """Assert that requests with the given method are ignored."""
        fd = StringIO(
            self.sample_line % dict(status='200', method=method))
        downloads, parsed_bytes = parse_file(fd, start_position=0)
        self.assertEqual(downloads, {})
        self.assertEqual(parsed_bytes, fd.tell())

    def test_HEAD_requests_are_ignored(self):
        self._assertRequestWithGivenMethodIsIgnored('HEAD')

    def test_POST_requests_are_ignored(self):
        self._assertRequestWithGivenMethodIsIgnored('POST')


class TestParsedFilesDetection(TestCase):
    """Test the detection of already parsed logs."""

    layer = LaunchpadZopelessLayer
    # The directory in which the sample log files live.
    root = os.path.join(here, 'apache-log-files')

    def setUp(self):
        self.layer.switchDbUser(DBUSER)

    def test_not_parsed_file(self):
        # A file that has never been parsed will have to be parsed from the
        # start.
        file_name = 'launchpadlibrarian.net.access-log'
        files_to_parse = get_files_to_parse(self.root, [file_name])
        self.failUnlessEqual(files_to_parse.values(), [0])

    def test_completely_parsed_file(self):
        # A file that has been completely parsed will be skipped.
        file_name = 'launchpadlibrarian.net.access-log'
        fd = open(os.path.join(self.root, file_name))
        first_line = fd.readline()
        fd.seek(0)
        ParsedApacheLog(first_line, len(fd.read()))

        self.failUnlessEqual(get_files_to_parse(self.root, [file_name]), {})

    def test_parsed_file_with_new_content(self):
        # A file that has been parsed already but in which new content was
        # added will be parsed again, starting from where parsing stopped last
        # time.
        file_name = 'launchpadlibrarian.net.access-log'
        first_line = open(os.path.join(self.root, file_name)).readline()
        ParsedApacheLog(first_line, len(first_line))

        files_to_parse = get_files_to_parse(self.root, [file_name])
        self.failUnlessEqual(files_to_parse.values(), [len(first_line)])

    def test_different_files_with_same_name(self):
        # Thanks to log rotation, two runs of our script may see files with
        # the same name but completely different content.  If we see a file 
        # with a name matching that of an already parsed file but with content
        # differing from the last file with that name parsed, we know we need
        # to parse the file from the start.
        ParsedApacheLog('First line', bytes_read=1000)

        # This file has the same name of the previous one (which has been
        # parsed already), but its first line is different, so we'll have to
        # parse it from the start.
        fd, file_name = tempfile.mkstemp()
        content2 = 'Different First Line\nSecond Line'
        fd = open(file_name, 'w')
        fd.write(content2)
        fd.close()
        files_to_parse = get_files_to_parse(self.root, [file_name])
        self.failUnlessEqual(files_to_parse.values(), [0])

    def test_gzipped_file(self):
        # get_files_to_parse() handles gzipped files just like uncompressed
        # ones.
        # The first time we see one, we'll parse from the beginning.
        file_name = 'launchpadlibrarian.net.access-log.1.gz'
        first_line = gzip.open(os.path.join(self.root, file_name)).readline()
        files_to_parse = get_files_to_parse(self.root, [file_name])
        self.failUnlessEqual(files_to_parse.values(), [0])

        # And in subsequent runs of the script we will resume from where we
        # stopped last time. (Here we pretend we parsed only the first line)
        ParsedApacheLog(first_line, len(first_line))
        files_to_parse = get_files_to_parse(self.root, [file_name])
        self.failUnlessEqual(files_to_parse.values(), [len(first_line)])


class Test_create_or_update_parsedlog_entry(TestCase):
    """Test the create_or_update_parsedlog_entry function."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        self.layer.switchDbUser(DBUSER)

    def test_creation_of_new_entries(self):
        # When given a first_line that doesn't exist in the ParsedApacheLog
        # table, create_or_update_parsedlog_entry() will create a new entry
        # with the given number of bytes read.
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        first_line = u'First line'
        create_or_update_parsedlog_entry(
            first_line, parsed_bytes=len(first_line))

        entry = store.find(ParsedApacheLog, first_line=first_line).one()
        self.assertIsNot(None, entry)
        self.assertEqual(entry.bytes_read, len(first_line))

    def test_update_of_existing_entries(self):
        # When given a first_line that already exists in the ParsedApacheLog
        # table, create_or_update_parsedlog_entry() will update that entry
        # with the given number of bytes read.
        first_line = u'First line'
        create_or_update_parsedlog_entry(first_line, parsed_bytes=2)
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        entry = store.find(ParsedApacheLog, first_line=first_line).one()

        # Here we see that the new entry was created.
        self.assertIsNot(None, entry)
        self.assertEqual(entry.bytes_read, 2)

        create_or_update_parsedlog_entry(
            first_line, parsed_bytes=len(first_line))

        # And here we see that same entry was updated by the second call to
        # create_or_update_parsedlog_entry().
        entry2 = store.find(ParsedApacheLog, first_line=first_line).one()
        self.assertIs(entry, entry2)
        self.assertIsNot(None, entry2)
        self.assertEqual(entry2.bytes_read, len(first_line))


class TestScriptRunning(TestCase):
    """Run parse-librarian-apache-access-logs.py and test its outcome."""

    layer = DatabaseFunctionalLayer

    def test_script_run(self):
        # Before we run the script, the LibraryFileAliases with id 1, 2 and 3
        # will have download counts set to 0.  After the script's run, each of
        # them will have their download counts set to 1, matching the sample
        # log files we use for this test:
        # scripts/tests/apache-log-files-for-sampledata.
        login(ANONYMOUS)
        libraryfile_set = getUtility(ILibraryFileAliasSet)
        self.assertEqual(libraryfile_set[1].hits, 0)
        self.assertEqual(libraryfile_set[2].hits, 0)
        self.assertEqual(libraryfile_set[3].hits, 0)

        process = subprocess.Popen(
            'cronscripts/parse-librarian-apache-access-logs.py', shell=True,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        (out, err) = process.communicate()
        self.assertEqual(
            process.returncode, 0, "stdout:%s, stderr:%s" % (out, err))

        # Must commit because the changes were done in another transaction.
        import transaction
        transaction.commit()
        self.assertEqual(libraryfile_set[1].hits, 1)
        self.assertEqual(libraryfile_set[2].hits, 1)
        self.assertEqual(libraryfile_set[3].hits, 1)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
