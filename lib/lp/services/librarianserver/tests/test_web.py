# Copyright 2009-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from datetime import datetime
from gzip import GzipFile
import hashlib
import httplib
from io import BytesIO
import os
import unittest
from urlparse import urlparse

from lazr.uri import URI
import pytz
import requests
from storm.expr import SQL
import testtools
from testtools.matchers import EndsWith
import transaction
from zope.component import getUtility

from lp.services.config import config
from lp.services.database.interfaces import IMasterStore
from lp.services.database.sqlbase import (
    cursor,
    flush_database_updates,
    session_store,
    )
from lp.services.librarian.client import (
    get_libraryfilealias_download_path,
    LibrarianClient,
    )
from lp.services.librarian.interfaces import ILibraryFileAliasSet
from lp.services.librarian.interfaces.client import DownloadFailed
from lp.services.librarian.model import (
    LibraryFileAlias,
    TimeLimitedToken,
    )
from lp.services.librarianserver.storage import LibrarianStorage
from lp.testing.dbuser import switch_dbuser
from lp.testing.layers import (
    LaunchpadFunctionalLayer,
    LaunchpadZopelessLayer,
    )


def uri_path_replace(url, old, new):
    """Replace a substring of a URL's path."""
    parsed = URI(url)
    return str(parsed.replace(path=parsed.path.replace(old, new)))


class LibrarianWebTestCase(testtools.TestCase):
    """Test the librarian's web interface."""
    layer = LaunchpadFunctionalLayer

    # Add stuff to a librarian via the upload port, then check that it's
    # immediately visible on the web interface. (in an attempt to test ddaa's
    # 500-error issue).

    def commit(self):
        """Synchronize database state."""
        flush_database_updates()
        transaction.commit()

    def test_uploadThenDownload(self):
        client = LibrarianClient()

        # Do this 10 times, to try to make sure we get all the threads in the
        # thread pool involved more than once, in case handling the second
        # request is an issue...
        for count in range(10):
            # Upload a file.  This should work without any exceptions being
            # thrown.
            sampleData = b'x' + (b'blah' * (count % 5))
            fileAlias = client.addFile('sample', len(sampleData),
                                                 BytesIO(sampleData),
                                                 contentType='text/plain')

            # Make sure we can get its URL
            url = client.getURLForAlias(fileAlias)

            # However, we can't access it until we have committed,
            # because the server has no idea what mime-type to send it as
            # (NB. This could be worked around if necessary by having the
            # librarian allow access to files that don't exist in the DB
            # and spitting them out with an 'unknown' mime-type
            # -- StuartBishop)
            self.require404(url)
            self.commit()

            # Make sure we can download it using the API
            fileObj = client.getFileByAlias(fileAlias)
            self.assertEqual(sampleData, fileObj.read())
            fileObj.close()

            # And make sure the URL works too
            response = requests.get(url)
            response.raise_for_status()
            self.assertEqual(sampleData, response.content)

    def test_checkGzipEncoding(self):
        # Files that end in ".txt.gz" are treated special and are returned
        # with an encoding of "gzip" or "x-gzip" to accomodate requirements of
        # displaying Ubuntu build logs in the browser.  The mimetype should be
        # "text/plain" for these files.
        client = LibrarianClient()
        contents = u'Build log \N{SNOWMAN}...'.encode('UTF-8')
        build_log = BytesIO()
        with GzipFile(mode='wb', fileobj=build_log) as f:
            f.write(contents)
        build_log.seek(0)
        alias_id = client.addFile(name="build_log.txt.gz",
                                  size=len(build_log.getvalue()),
                                  file=build_log,
                                  contentType="text/plain")

        self.commit()

        url = client.getURLForAlias(alias_id)
        response = requests.get(url)
        response.raise_for_status()
        mimetype = response.headers['content-type']
        encoding = response.headers['content-encoding']
        self.assertTrue(mimetype == "text/plain; charset=utf-8",
                        "Wrong mimetype. %s != 'text/plain'." % mimetype)
        self.assertTrue(encoding == "gzip",
                        "Wrong encoding. %s != 'gzip'." % encoding)
        self.assertEqual(contents.decode('UTF-8'), response.text)

    def test_checkNoEncoding(self):
        # Other files should have no encoding.
        client = LibrarianClient()
        contents = b'Build log...'
        build_log = BytesIO(contents)
        alias_id = client.addFile(name="build_log.tgz",
                                  size=len(contents),
                                  file=build_log,
                                  contentType="application/x-tar")

        self.commit()

        url = client.getURLForAlias(alias_id)
        response = requests.get(url)
        response.raise_for_status()
        mimetype = response.headers['content-type']
        self.assertNotIn('content-encoding', response.headers)
        self.assertTrue(
            mimetype == "application/x-tar",
            "Wrong mimetype. %s != 'application/x-tar'." % mimetype)

    def test_aliasNotFound(self):
        client = LibrarianClient()
        self.assertRaises(DownloadFailed, client.getURLForAlias, 99)

    def test_oldurl(self):
        # 'old' urls are in the form of http://server:port/cid/aid/fname
        # which we want to continue supporting. The content id is simply
        # ignored
        client = LibrarianClient()
        filename = 'sample.txt'
        aid = client.addFile(filename, 6, BytesIO(b'sample'), 'text/plain')
        self.commit()
        url = client.getURLForAlias(aid)
        response = requests.get(url)
        response.raise_for_status()
        self.assertEqual(response.content, b'sample')

        old_url = uri_path_replace(url, str(aid), '42/%d' % aid)
        response = requests.get(url)
        response.raise_for_status()
        self.assertEqual(response.content, b'sample')

        # If the content and alias IDs are not integers, a 404 is raised
        old_url = uri_path_replace(url, str(aid), 'foo/%d' % aid)
        self.require404(old_url)
        old_url = uri_path_replace(url, str(aid), '%d/foo' % aid)
        self.require404(old_url)

    def test_404(self):
        client = LibrarianClient()
        filename = 'sample.txt'
        aid = client.addFile(filename, 6, BytesIO(b'sample'), 'text/plain')
        self.commit()
        url = client.getURLForAlias(aid)
        response = requests.get(url)
        response.raise_for_status()
        self.assertEqual(response.content, b'sample')

        # Change the aliasid and assert we get a 404
        self.assertIn(str(aid), url)
        bad_id_url = uri_path_replace(url, str(aid), str(aid + 1))
        self.require404(bad_id_url)

        # Change the filename and assert we get a 404
        self.assertIn(filename, url)
        bad_name_url = uri_path_replace(url, filename, 'different.txt')
        self.require404(bad_name_url)

    def test_duplicateuploads(self):
        client = LibrarianClient()
        filename = 'sample.txt'
        id1 = client.addFile(filename, 6, BytesIO(b'sample'), 'text/plain')
        id2 = client.addFile(filename, 6, BytesIO(b'sample'), 'text/plain')

        self.assertNotEqual(id1, id2, 'Got allocated the same id!')

        self.commit()

        self.assertEqual(client.getFileByAlias(id1).read(), b'sample')
        self.assertEqual(client.getFileByAlias(id2).read(), b'sample')

    def test_robotsTxt(self):
        url = 'http://%s:%d/robots.txt' % (
            config.librarian.download_host, config.librarian.download_port)
        response = requests.get(url)
        response.raise_for_status()
        self.assertIn('Disallow: /', response.text)

    def test_headers(self):
        client = LibrarianClient()

        # Upload a file so we can retrieve it.
        sample_data = b'blah'
        file_alias_id = client.addFile(
            'sample', len(sample_data), BytesIO(sample_data),
            contentType='text/plain')
        url = client.getURLForAlias(file_alias_id)

        # Change the date_created to a known value that doesn't match
        # the disk timestamp. The timestamp on disk cannot be trusted.
        file_alias = IMasterStore(LibraryFileAlias).get(
            LibraryFileAlias, file_alias_id)
        file_alias.date_created = datetime(
            2001, 1, 30, 13, 45, 59, tzinfo=pytz.utc)

        # Commit so the file is available from the Librarian.
        self.commit()

        # Fetch the file via HTTP, recording the interesting headers
        response = requests.get(url)
        response.raise_for_status()
        last_modified_header = response.headers['Last-Modified']
        cache_control_header = response.headers['Cache-Control']

        # URLs point to the same content for ever, so we have a hardcoded
        # 1 year max-age cache policy.
        self.assertEqual(cache_control_header, 'max-age=31536000, public')

        # And we should have a correct Last-Modified header too.
        self.assertEqual(
            last_modified_header, 'Tue, 30 Jan 2001 13:45:59 GMT')

    def test_missing_storage(self):
        # When a file exists in the DB but is missing from disk, a 404
        # is just confusing. It's an internal error, so 500 instead.
        client = LibrarianClient()

        # Upload a file so we can retrieve it.
        sample_data = b'blah'
        file_alias_id = client.addFile(
            'sample', len(sample_data), BytesIO(sample_data),
            contentType='text/plain')
        url = client.getURLForAlias(file_alias_id)

        # Change the date_created to a known value that doesn't match
        # the disk timestamp. The timestamp on disk cannot be trusted.
        file_alias = IMasterStore(LibraryFileAlias).get(
            LibraryFileAlias, file_alias_id)

        # Commit so the file is available from the Librarian.
        self.commit()

        # Fetch the file via HTTP.
        response = requests.get(url)
        response.raise_for_status()

        # Delete the on-disk file.
        storage = LibrarianStorage(config.librarian_server.root, None)
        os.remove(storage._fileLocation(file_alias.contentID))

        # The URL now 500s, since the DB says it should exist.
        response = requests.get(url)
        self.assertEqual(500, response.status_code)
        self.assertIn('Server', response.headers)
        self.assertNotIn('Last-Modified', response.headers)
        self.assertNotIn('Cache-Control', response.headers)

    def get_restricted_file_and_public_url(self, filename='sample'):
        # Use a regular LibrarianClient to ensure we speak to the
        # nonrestricted port on the librarian which is where secured
        # restricted files are served from.
        client = LibrarianClient()
        fileAlias = client.addFile(
            filename, 12, BytesIO(b'a' * 12), contentType='text/plain')
        # Note: We're deliberately using the wrong url here: we should be
        # passing secure=True to getURLForAlias, but to use the returned URL
        # we would need a wildcard DNS facility patched into requests; instead
        # we use the *deliberate* choice of having the path of secure and
        # insecure urls be the same, so that we can test it: the server code
        # doesn't need to know about the fancy wildcard domains.
        url = client.getURLForAlias(fileAlias)
        # Now that we have a url which talks to the public librarian, make the
        # file restricted.
        IMasterStore(LibraryFileAlias).find(
            LibraryFileAlias, LibraryFileAlias.id == fileAlias).set(
                restricted=True)
        self.commit()
        return fileAlias, url

    def test_restricted_subdomain_must_match_file_alias(self):
        # IFF there is a .restricted. in the host, then the library file alias
        # in the subdomain must match that in the path.
        client = LibrarianClient()
        fileAlias = client.addFile('sample', 12, BytesIO(b'a' * 12),
            contentType='text/plain')
        fileAlias2 = client.addFile('sample', 12, BytesIO(b'b' * 12),
            contentType='text/plain')
        self.commit()
        url = client.getURLForAlias(fileAlias)
        download_host = urlparse(config.librarian.download_url)[1]
        if ':' in download_host:
            download_host = download_host[:download_host.find(':')]
        template_host = 'i%%d.restricted.%s' % download_host
        path = get_libraryfilealias_download_path(fileAlias, 'sample')
        # The basic URL must work.
        response = requests.get(url)
        response.raise_for_status()
        # Use the network level protocol because DNS resolution won't work
        # here (no wildcard support)
        connection = httplib.HTTPConnection(
            config.librarian.download_host,
            config.librarian.download_port)
        # A valid subdomain based URL must work.
        good_host = template_host % fileAlias
        connection.request("GET", path, headers={'Host': good_host})
        response = connection.getresponse()
        response.read()
        self.assertEqual(200, response.status, response)
        # A subdomain based URL trying to put fileAlias into the restricted
        # domain of fileAlias2 must not work.
        hostile_host = template_host % fileAlias2
        connection.request("GET", path, headers={'Host': hostile_host})
        response = connection.getresponse()
        response.read()
        self.assertEqual(404, response.status)
        # A subdomain which matches the LFA but is nested under one that
        # doesn't is also treated as hostile.
        nested_host = 'i%d.restricted.i%d.restricted.%s' % (
            fileAlias, fileAlias2, download_host)
        connection.request("GET", path, headers={'Host': nested_host})
        response = connection.getresponse()
        response.read()
        self.assertEqual(404, response.status)

    def test_restricted_no_token(self):
        fileAlias, url = self.get_restricted_file_and_public_url()
        # The file should not be able to be opened - we haven't allocated a
        # token.  When the token is wrong or stale a 404 is given (to avoid
        # disclosure about what content we hold. Alternatively a 401 could be
        # given (as long as we give a 401 when the file is missing as well -
        # but that requires some more complex changes in the deployment
        # infrastructure to permit more backend knowledge of the frontend
        # request.
        self.require404(url)

    def test_restricted_made_up_token(self):
        fileAlias, url = self.get_restricted_file_and_public_url()
        # The file should not be able to be opened - the token supplied
        # is not one we issued.
        self.require404(url, params={"token": "haxx0r"})

    def test_restricted_with_token(self):
        fileAlias, url = self.get_restricted_file_and_public_url()
        # We have the base url for a restricted file; grant access to it
        # for a short time.
        token = TimeLimitedToken.allocate(url)
        # Now we should be able to access the file.
        response = requests.get(url, params={"token": token})
        response.raise_for_status()
        self.assertEqual(b"a" * 12, response.content)

    def test_restricted_with_token_encoding(self):
        fileAlias, url = self.get_restricted_file_and_public_url('foo~%')
        self.assertThat(url, EndsWith('/foo~%25'))

        # We have the base url for a restricted file; grant access to it
        # for a short time.
        token = TimeLimitedToken.allocate(url)

        # Now we should be able to access the file.
        response = requests.get(url, params={"token": token})
        response.raise_for_status()
        self.assertEqual(b"a" * 12, response.content)

        # The token is valid even if the filename is encoded differently.
        mangled_url = url.replace('~', '%7E')
        self.assertNotEqual(mangled_url, url)
        response = requests.get(url, params={"token": token})
        response.raise_for_status()
        self.assertEqual(b"a" * 12, response.content)

    def test_restricted_with_expired_token(self):
        fileAlias, url = self.get_restricted_file_and_public_url()
        # We have the base url for a restricted file; grant access to it
        # for a short time.
        token = TimeLimitedToken.allocate(url)
        # But time has passed
        store = session_store()
        tokens = store.find(
            TimeLimitedToken,
            TimeLimitedToken.token == hashlib.sha256(token).hexdigest())
        tokens.set(
            TimeLimitedToken.created == SQL("created - interval '1 week'"))
        # Now, as per test_restricted_no_token we should get a 404.
        self.require404(url, params={"token": token})

    def test_restricted_file_headers(self):
        fileAlias, url = self.get_restricted_file_and_public_url()
        token = TimeLimitedToken.allocate(url)
        # Change the date_created to a known value for testing.
        file_alias = IMasterStore(LibraryFileAlias).get(
            LibraryFileAlias, fileAlias)
        file_alias.date_created = datetime(
            2001, 1, 30, 13, 45, 59, tzinfo=pytz.utc)
        # Commit the update.
        self.commit()
        # Fetch the file via HTTP, recording the interesting headers
        response = requests.get(url, params={"token": token})
        last_modified_header = response.headers['Last-Modified']
        cache_control_header = response.headers['Cache-Control']
        # No caching for restricted files.
        self.assertEqual(cache_control_header, 'max-age=0, private')
        # And we should have a correct Last-Modified header too.
        self.assertEqual(
            last_modified_header, 'Tue, 30 Jan 2001 13:45:59 GMT')
        # Perhaps we should also set Expires to the Last-Modified.

    def require404(self, url, **kwargs):
        """Assert that opening `url` raises a 404."""
        response = requests.get(url, **kwargs)
        self.assertEqual(404, response.status_code)


class LibrarianZopelessWebTestCase(LibrarianWebTestCase):
    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(LibrarianZopelessWebTestCase, self).setUp()
        switch_dbuser(config.librarian.dbuser)

    def commit(self):
        LaunchpadZopelessLayer.commit()

    def test_getURLForAliasObject(self):
        # getURLForAliasObject returns the same URL as getURLForAlias.
        client = LibrarianClient()
        content = b"Test content"
        alias_id = client.addFile(
            'test.txt', len(content), BytesIO(content),
            contentType='text/plain')
        self.commit()

        alias = getUtility(ILibraryFileAliasSet)[alias_id]
        self.assertEqual(
            client.getURLForAlias(alias_id),
            client.getURLForAliasObject(alias))


class DeletedContentTestCase(unittest.TestCase):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(DeletedContentTestCase, self).setUp()
        switch_dbuser(config.librarian.dbuser)

    def test_deletedContentNotFound(self):
        # Use a user with rights to change the deleted flag in the db.
        # This currently means a superuser.
        switch_dbuser('testadmin')

        alias = getUtility(ILibraryFileAliasSet).create(
                'whatever', 8, BytesIO(b'xxx\nxxx\n'), 'text/plain')
        alias_id = alias.id
        transaction.commit()

        # This works
        alias = getUtility(ILibraryFileAliasSet)[alias_id]
        alias.open()
        alias.read()
        alias.close()

        # And it can be retrieved via the web
        url = alias.http_url
        response = requests.get(url)
        response.raise_for_status()
        self.assertEqual(response.content, b'xxx\nxxx\n')

        # But when we flag the content as deleted
        cur = cursor()
        cur.execute("""
            UPDATE LibraryFileAlias SET content=NULL WHERE id=%s
            """, (alias.id, ))
        transaction.commit()

        # Things become not found
        alias = getUtility(ILibraryFileAliasSet)[alias_id]
        self.assertRaises(DownloadFailed, alias.open)

        # And people see a 404 page
        response = requests.get(url)
        self.assertEqual(404, response.status_code)
