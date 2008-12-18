# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type

import os
import signal
import subprocess
import unittest
import xmlrpclib

from canonical.codehosting import branch_id_to_path
from canonical.codehosting.inmemory import InMemoryFrontend, XMLRPCWrapper
from canonical.codehosting.rewrite import BranchRewriter
from canonical.config import config
from canonical.launchpad.testing import TestCase, TestCaseWithFactory
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
        rewriter = self.makeRewriter()
        branch = self.factory.makeBranch()
        line = rewriter.rewriteLine("/%s/.bzr/README" % branch.unique_name)
        self.assertEqual("/%s/.bzr/README" % branch_id_to_path(branch.id), line)

    def test_translateLine_found_not_dot_bzr(self):
        rewriter = self.makeRewriter()
        branch = self.factory.makeBranch()
        input = "/%s/changes" % branch.unique_name
        output = rewriter.rewriteLine(input)
        self.assertEqual(
            config.codehosting.internal_codebrowse_root + input, output)

    def test_translateLine_not_found(self):
        rewriter = self.makeRewriter()
        input = "/~no-user/no-product/no-branch/changes"
        self.assertRaises(xmlrpclib.Fault, rewriter.rewriteLine, input)



class TestBranchRewriterScript(TestCaseWithFactory):

    layer = ZopelessAppServerLayer

    def test_script(self):
        branch = self.factory.makeBranch()
        input = "/%s/.bzr/README\n" % branch.unique_name
        expected = "/%s/.bzr/README\n" % branch_id_to_path(branch.id)
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
        self.assertEqual(expected, output)
        # XXX MichaelHudson, bug=???: Logging!
        #self.assertEqual('', err)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

