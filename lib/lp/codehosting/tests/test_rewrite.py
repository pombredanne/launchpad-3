# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the dynamic RewriteMap used to serve branches over HTTP."""

__metaclass__ = type

import os
import signal
import subprocess
import unittest

from lp.codehosting.vfs import branch_id_to_path
from lp.codehosting.inmemory import InMemoryFrontend, XMLRPCWrapper
from lp.codehosting.rewrite import BranchRewriter
from canonical.config import config
from lp.testing import TestCase, TestCaseWithFactory
from canonical.launchpad.scripts import QuietFakeLogger
from canonical.testing.layers import ZopelessAppServerLayer


class TestBranchRewriter(TestCase):

    def setUp(self):
        frontend = InMemoryFrontend()
        self._branchfs = frontend.getFilesystemEndpoint()
        self.factory = frontend.getLaunchpadObjectFactory()

    def makeRewriter(self):
        return BranchRewriter(
            QuietFakeLogger(), XMLRPCWrapper(self._branchfs))

    def test_translateLine_found_dot_bzr(self):
        # Requests for /$branch_name/.bzr/... are redirected to where the
        # branches are served from by ID.
        rewriter = self.makeRewriter()
        branch = self.factory.makeAnyBranch()
        line = rewriter.rewriteLine("/%s/.bzr/README" % branch.unique_name)
        self.assertEqual(
            'file:///var/tmp/bzrsync/%s/.bzr/README'
            % branch_id_to_path(branch.id),
            line)

    def test_translateLine_found_not_dot_bzr(self):
        # Requests for /$branch_name/... that are not to .bzr directories are
        # redirected to codebrowse.
        rewriter = self.makeRewriter()
        branch = self.factory.makeAnyBranch()
        output = rewriter.rewriteLine("/%s/changes" % branch.unique_name)
        self.assertEqual(
            'http://localhost:8080/%s/changes' % branch.unique_name,
            output)

    def test_translateLine_private(self):
        # All requests for /$branch_name/... for private branches are
        # rewritten to codebrowse, which will then redirect them to https and
        # handle them there.
        rewriter = self.makeRewriter()
        branch = self.factory.makeBranch(private=True)
        output = rewriter.rewriteLine("/%s/changes" % branch.unique_name)
        self.assertEqual(
            'http://localhost:8080/%s/changes' % branch.unique_name,
            output)
        output = rewriter.rewriteLine("/%s/.bzr" % branch.unique_name)
        self.assertEqual(
            'http://localhost:8080/%s/.bzr' % branch.unique_name,
            output)

    def test_translateLine_static(self):
        # Requests to /static are rewritten to codebrowse urls.
        rewriter = self.makeRewriter()
        output = rewriter.rewriteLine("/static/foo")
        self.assertEqual(
            'http://localhost:8080/static/foo',
            output)

    def test_translateLine_not_found(self):
        # If the request does not map to a branch, we redirect it to
        # codebrowse as it can generate a 404.
        rewriter = self.makeRewriter()
        not_found_path = "/~nouser/noproduct"
        output = rewriter.rewriteLine(not_found_path)
        self.assertEqual(
            'http://localhost:8080%s' % not_found_path,
            output)


class TestBranchRewriterScript(TestCaseWithFactory):

    layer = ZopelessAppServerLayer

    def test_script(self):
        branch = self.factory.makeAnyBranch()
        input = "/%s/.bzr/README\n" % branch.unique_name
        expected = (
            "file:///var/tmp/bzrsync/%s/.bzr/README\n"
            % branch_id_to_path(branch.id))
        self.layer.txn.commit()
        script_file = os.path.join(
            config.root, 'scripts', 'branch-rewrite.py')
        proc = subprocess.Popen(
            [script_file], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, bufsize=0)
        proc.stdin.write(input)
        output = proc.stdout.readline()
        os.kill(proc.pid, signal.SIGINT)
        err = proc.stderr.read()
        # The script produces logging output, but not to stderr.
        self.assertEqual('', err)
        self.assertEqual(expected, output)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

