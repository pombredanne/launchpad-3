# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the script run on the remote server."""

__metaclass__ = type

import gzip
import os
from StringIO import StringIO
import sys
import tempfile
import unittest

from bzrlib.tests import TestCaseWithTransport

from testtools import TestCase

from devscripts.ec2test.remote import (
    FlagFallStream,
    gzip_file,
    remove_pidfile,
    Request,
    SummaryResult,
    write_pidfile,
    )


class TestFlagFallStream(TestCase):
    """Tests for `FlagFallStream`."""

    def test_doesnt_write_before_flag(self):
        # A FlagFallStream does not forward any writes before it sees the
        # 'flag'.
        stream = StringIO()
        flag = self.getUniqueString('flag')
        flagfall = FlagFallStream(stream, flag)
        flagfall.write('foo')
        flagfall.flush()
        self.assertEqual('', stream.getvalue())

    def test_writes_after_flag(self):
        # After a FlagFallStream sees the flag, it forwards all writes.
        stream = StringIO()
        flag = self.getUniqueString('flag')
        flagfall = FlagFallStream(stream, flag)
        flagfall.write('foo')
        flagfall.write(flag)
        flagfall.write('bar')
        self.assertEqual('%sbar' % (flag,), stream.getvalue())

    def test_mixed_write(self):
        # If a single call to write has pre-flagfall and post-flagfall data in
        # it, then only the post-flagfall data is forwarded to the stream.
        stream = StringIO()
        flag = self.getUniqueString('flag')
        flagfall = FlagFallStream(stream, flag)
        flagfall.write('foo%sbar' % (flag,))
        self.assertEqual('%sbar' % (flag,), stream.getvalue())


class TestSummaryResult(TestCase):
    """Tests for `SummaryResult`."""

    def makeException(self, factory=None, *args, **kwargs):
        if factory is None:
            factory = RuntimeError
        try:
            raise factory(*args, **kwargs)
        except:
            return sys.exc_info()

    def test_formatError(self):
        # SummaryResult._formatError() combines the name of the test, the kind
        # of error and the details of the error in a nicely-formatted way.
        result = SummaryResult(None)
        output = result._formatError('FOO', 'test', 'error')
        expected = '%s\nFOO: test\n%s\nerror\n' % (
            result.double_line, result.single_line)
        self.assertEqual(expected, output)

    def test_addError(self):
        # SummaryResult.addError doesn't write immediately.
        stream = StringIO()
        test = self
        error = self.makeException()
        result = SummaryResult(stream)
        expected = result._formatError(
            'ERROR', test, result._exc_info_to_string(error, test))
        result.addError(test, error)
        self.assertEqual(expected, stream.getvalue())

    def test_addFailure_does_not_write_immediately(self):
        # SummaryResult.addFailure doesn't write immediately.
        stream = StringIO()
        test = self
        error = self.makeException()
        result = SummaryResult(stream)
        expected = result._formatError(
            'FAILURE', test, result._exc_info_to_string(error, test))
        result.addFailure(test, error)
        self.assertEqual(expected, stream.getvalue())


class TestPidfileHelpers(TestCase):
    """Tests for `write_pidfile` and `remove_pidfile`."""

    def test_write_pidfile(self):
        fd, path = tempfile.mkstemp()
        self.addCleanup(os.unlink, path)
        os.close(fd)
        write_pidfile(path)
        self.assertEqual(os.getpid(), int(open(path, 'r').read()))

    def test_remove_pidfile(self):
        fd, path = tempfile.mkstemp()
        os.close(fd)
        write_pidfile(path)
        remove_pidfile(path)
        self.assertEqual(False, os.path.exists(path))

    def test_remove_nonexistent_pidfile(self):
        directory = tempfile.mkdtemp()
        path = os.path.join(directory, 'doesntexist')
        remove_pidfile(path)
        self.assertEqual(False, os.path.exists(path))


class TestGzipFile(TestCase):
    """Tests for `gzip_file`."""

    def test_gzip_file(self):
        fd, path = tempfile.mkstemp()
        contents = 'foobarbaz\n'
        os.write(fd, contents)
        os.close(fd)
        gz_file = gzip_file(path)
        self.assertEqual(contents, gzip.open(gz_file, 'r').read())


class TestRequest(TestCaseWithTransport):
    """Tests for `Request`."""

    def make_trunk(self, parent_url='http://example.com/bzr/trunk'):
        """Make a trunk branch suitable for use with `Request`.

        `Request` expects to be given a path to a working tree that has a
        branch with a configured parent URL, so this helper returns such a
        working tree.
        """
        nick = parent_url.strip('/').split('/')[-1]
        tree = self.make_branch_and_tree(nick)
        tree.branch.set_parent(parent_url)
        return tree

    def make_request(self, branch_url=None, revno=None,
                     trunk=None, sourcecode_path=None,
                     emails=None, pqm_message=None):
        """Make a request to test, specifying only things we care about."""
        if trunk is None:
            trunk = self.make_trunk()
        return Request(
            branch_url, revno, trunk.basedir, sourcecode_path, emails,
            pqm_message)

    def test_doesnt_want_email(self):
        # If no email addresses were provided, then the user does not want to
        # receive email.
        req = self.make_request()
        self.assertEqual(False, req.wants_email)

    def test_wants_email(self):
        # If some email addresses were provided, then the user wants to
        # receive email.
        req = self.make_request(emails=['foo@example.com'])
        self.assertEqual(True, req.wants_email)

    def test_get_trunk_details(self):
        parent = 'http://example.com/bzr/branch'
        tree = self.make_trunk(parent)
        req = self.make_request(trunk=tree)
        self.assertEqual(
            (parent, tree.branch.revno()), req.get_trunk_details())

    def test_get_branch_details_no_commits(self):
        req = self.make_request(trunk=self.make_trunk())
        self.assertEqual(None, req.get_branch_details())

    def test_get_branch_details_no_merge(self):
        tree = self.make_trunk()
        tree.commit(message='foo')
        req = self.make_request(trunk=tree)
        self.assertEqual(None, req.get_branch_details())

    def test_get_branch_details_merge(self):
        tree = self.make_trunk()
        # Fake a merge, giving silly revision ids.
        tree.add_pending_merge('foo', 'bar')
        req = self.make_request(
            branch_url='https://example.com/bzr/thing', revno=42, trunk=tree)
        self.assertEqual(
            ('https://example.com/bzr/thing', 42), req.get_branch_details())

    def test_get_nick_trunk_only(self):
        tree = self.make_trunk(parent_url='http://example.com/bzr/db-devel')
        req = self.make_request(trunk=tree)
        self.assertEqual('db-devel', req.get_nick())

    def test_get_nick_merge(self):
        tree = self.make_trunk()
        # Fake a merge, giving silly revision ids.
        tree.add_pending_merge('foo', 'bar')
        req = self.make_request(
            branch_url='https://example.com/bzr/thing', revno=42, trunk=tree)
        self.assertEqual('thing', req.get_nick())

    def test_get_merge_description_trunk_only(self):
        tree = self.make_trunk(parent_url='http://example.com/bzr/db-devel')
        req = self.make_request(trunk=tree)
        self.assertEqual('db-devel', req.get_merge_description())

    def test_get_merge_description_merge(self):
        tree = self.make_trunk(parent_url='http://example.com/bzr/db-devel/')
        tree.add_pending_merge('foo', 'bar')
        req = self.make_request(
            branch_url='https://example.com/bzr/thing', revno=42, trunk=tree)
        self.assertEqual('thing => db-devel', req.get_merge_description())

    def test_get_summary_commit(self):
        # The summary commit message is the last commit message of the branch
        # we're merging in.
        trunk = self.make_trunk()
        trunk.commit(message="a starting point")
        thing_bzrdir = trunk.branch.bzrdir.sprout('thing')
        thing = thing_bzrdir.open_workingtree()
        thing.commit(message="a new thing")
        trunk.merge_from_branch(thing.branch)
        req = self.make_request(
            branch_url='https://example.com/bzr/thing',
            revno=thing.branch.revno(),
            trunk=trunk)
        self.assertEqual("a new thing", req.get_summary_commit())

    def test_iter_dependency_branches(self):
        # iter_dependency_branches yields a list of branches in the sourcecode
        # directory, along with their parent URLs and their revnos.
        sourcecode_branches = [
            ('b', 'http://example.com/parent-b', 3),
            ('a', 'http://example.com/parent-a', 2),
            ('c', 'http://example.com/parent-c', 5),
            ]
        self.build_tree(
            ['sourcecode/',
             'sourcecode/not-a-branch/',
             'sourcecode/just-a-file'])
        for name, parent_url, revno in sourcecode_branches:
            tree = self.make_branch_and_tree('sourcecode/%s' % (name,))
            tree.branch.set_parent(parent_url)
            for i in range(revno):
                tree.commit(message=str(i))
        req = self.make_request(sourcecode_path='sourcecode/')
        branches = list(req.iter_dependency_branches())
        self.assertEqual(sorted(sourcecode_branches), branches)

    def test_submit_to_pqm_no_message(self):
        # If there's no PQM message, then 'submit_to_pqm' returns None.
        req = self.make_request(pqm_message=None)
        subject = req.submit_to_pqm(successful=True)
        self.assertIs(None, subject)

    def test_submit_to_pqm_no_message_doesnt_send(self):
        # If there's no PQM message, then 'submit_to_pqm' returns None.
        emails = []
        req = self.make_request(pqm_message=None)
        req._send_email = emails.append
        req.submit_to_pqm(successful=True)
        self.assertEqual([], emails)

    def test_submit_to_pqm_unsuccessful(self):
        # submit_to_pqm returns the subject of the PQM mail even if it's
        # handling a failed test run.
        message = {'Subject:': 'My PQM message'}
        req = self.make_request(pqm_message=message)
        subject = req.submit_to_pqm(successful=False)
        self.assertIs(message.get('Subject'), subject)

    def test_submit_to_pqm_unsuccessful_no_email(self):
        # submit_to_pqm doesn't send any email if the run was unsuccessful.
        message = {'Subject:': 'My PQM message'}
        emails = []
        req = self.make_request(pqm_message=message)
        req._send_email = emails.append
        req.submit_to_pqm(successful=False)
        self.assertEqual([], emails)

    def test_submit_to_pqm_successful(self):
        # submit_to_pqm returns the subject of the PQM mail.
        message = {'Subject:': 'My PQM message'}
        emails = []
        req = self.make_request(pqm_message=message)
        req._send_email = emails.append
        subject = req.submit_to_pqm(successful=True)
        self.assertIs(message.get('Subject'), subject)
        self.assertEqual([message], emails)

    def test_report_email_subject_success(self):
        req = self.make_request(emails=['foo@example.com'])
        email = req._build_report_email(True, 'foo', 'gobbledygook')
        self.assertEqual('Test results: SUCCESS', email['Subject'])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)
