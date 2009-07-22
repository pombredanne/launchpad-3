# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the dynamic RewriteMap used to serve branches over HTTP."""

__metaclass__ = type

import re
import os
import signal
import subprocess
import unittest

import transaction

from zope.security.proxy import removeSecurityProxy

from lp.codehosting.vfs import branch_id_to_path
from lp.codehosting.rewrite import BranchRewriter
from canonical.config import config
from lp.testing import FakeTime, TestCaseWithFactory
from canonical.launchpad.scripts import BufferLogger
from canonical.testing.layers import DatabaseFunctionalLayer


class TestBranchRewriter(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.fake_time = FakeTime(0)

    def makeRewriter(self):
        return BranchRewriter(BufferLogger(), self.fake_time.now)

    def getLoggerOutput(self, rewriter):
        return rewriter.logger.buffer.getvalue()

    def test_rewriteLine_found_dot_bzr(self):
        # Requests for /$branch_name/.bzr/... are redirected to where the
        # branches are served from by ID.
        rewriter = self.makeRewriter()
        branches = [
            self.factory.makeProductBranch(),
            self.factory.makePersonalBranch(),
            self.factory.makePackageBranch()]
        transaction.commit()
        output = [
            rewriter.rewriteLine("/%s/.bzr/README" % branch.unique_name)
            for branch in branches]
        expected = [
            'file:///var/tmp/bzrsync/%s/.bzr/README'
            % branch_id_to_path(branch.id)
            for branch in branches]
        self.assertEqual(expected, output)

    def test_rewriteLine_found_not_dot_bzr(self):
        # Requests for /$branch_name/... that are not to .bzr directories are
        # redirected to codebrowse.
        rewriter = self.makeRewriter()
        branches = [
            self.factory.makeProductBranch(),
            self.factory.makePersonalBranch(),
            self.factory.makePackageBranch()]
        transaction.commit()
        output = [
            rewriter.rewriteLine("/%s/changes" % branch.unique_name)
            for branch in branches]
        expected = [
            'http://localhost:8080/%s/changes' % branch.unique_name
            for branch in branches]
        self.assertEqual(expected, output)

    def test_rewriteLine_private(self):
        # All requests for /$branch_name/... for private branches are
        # rewritten to codebrowse, which will then redirect them to https and
        # handle them there.
        rewriter = self.makeRewriter()
        branch = self.factory.makeAnyBranch(private=True)
        unique_name = removeSecurityProxy(branch).unique_name
        transaction.commit()
        output = [
            rewriter.rewriteLine("/%s/changes" % unique_name),
            rewriter.rewriteLine("/%s/.bzr" % unique_name)
            ]
        self.assertEqual(
            ['http://localhost:8080/%s/changes' % unique_name,
             'http://localhost:8080/%s/.bzr' % unique_name],
            output)

    def test_rewriteLine_static(self):
        # Requests to /static are rewritten to codebrowse urls.
        rewriter = self.makeRewriter()
        output = rewriter.rewriteLine("/static/foo")
        self.assertEqual(
            'http://localhost:8080/static/foo',
            output)

    def test_rewriteLine_not_found(self):
        # If the request does not map to a branch, we redirect it to
        # codebrowse as it can generate a 404.
        rewriter = self.makeRewriter()
        not_found_path = "/~nouser/noproduct"
        output = rewriter.rewriteLine(not_found_path)
        self.assertEqual(
            'http://localhost:8080%s' % not_found_path,
            output)

    def test_rewriteLine_logs_cache_miss(self):
        # The first request for a branch misses the cache and logs this fact.
        rewriter = self.makeRewriter()
        branch = self.factory.makeAnyBranch()
        transaction.commit()
        rewriter.rewriteLine('/' + branch.unique_name + '/.bzr/README')
        logging_output = self.getLoggerOutput(rewriter)
        self.assertIsNot(
            None,
            re.match("INFO: .* -> .* (.*s, cache: MISS)", logging_output),
            "No miss found in %r" % logging_output)

    def test_rewriteLine_logs_cache_hit(self):
        # The second request for a branch misses the cache and logs this fact.
        rewriter = self.makeRewriter()
        branch = self.factory.makeAnyBranch()
        transaction.commit()
        rewriter.rewriteLine('/' + branch.unique_name + '/.bzr/README')
        rewriter.rewriteLine('/' + branch.unique_name + '/.bzr/README')
        logging_output_lines = self.getLoggerOutput(rewriter).strip().split('\n')
        self.assertEqual(2, len(logging_output_lines))
        self.assertIsNot(
            None,
            re.match("INFO: .* -> .* (.*s, cache: HIT)",
                     logging_output_lines[-1]),
            "No hit found in %r" % logging_output_lines[-1])

    def test_rewriteLine_cache_expires(self):
        # The second request for a branch misses the cache and logs this fact.
        rewriter = self.makeRewriter()
        branch = self.factory.makeAnyBranch()
        transaction.commit()
        rewriter.rewriteLine('/' + branch.unique_name + '/.bzr/README')
        self.fake_time.advance(
            config.codehosting.branch_rewrite_cache_lifetime + 1)
        rewriter.rewriteLine('/' + branch.unique_name + '/.bzr/README')
        logging_output_lines = self.getLoggerOutput(rewriter).strip().split('\n')
        self.assertEqual(2, len(logging_output_lines))
        self.assertIsNot(
            None,
            re.match("INFO: .* -> .* (.*s, cache: MISS)",
                     logging_output_lines[-1]),
            "No miss found in %r" % logging_output_lines[-1])


class TestBranchRewriterScript(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_script(self):
        branches = [
            self.factory.makeProductBranch(),
            self.factory.makePersonalBranch(),
            self.factory.makePackageBranch()]
        input = [
            "/%s/.bzr/README" % branch.unique_name
            for branch in branches] + [
            "/%s/changes" % branch.unique_name
            for branch in branches]
        expected = [
            'file:///var/tmp/bzrsync/%s/.bzr/README'
            % branch_id_to_path(branch.id)
            for branch in branches] + [
            'http://localhost:8080/%s/changes' % branch.unique_name
            for branch in branches]
        transaction.commit()
        script_file = os.path.join(
            config.root, 'scripts', 'branch-rewrite.py')
        proc = subprocess.Popen(
            [script_file], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, bufsize=0)
        proc.stdin.write('\n'.join(input) + '\n')
        output = []
        for i in range(len(input)):
            output.append(proc.stdout.readline())
        os.kill(proc.pid, signal.SIGINT)
        err = proc.stderr.read()
        # The script produces logging output, but not to stderr.
        self.assertEqual('', err)
        self.assertEqual('\n'.join(expected) + '\n', ''.join(output))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

