#! /usr/bin/python
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import os.path
import sys
import tarfile

import logging

from bzrlib.branch import Branch
from bzrlib.export import export

from canonical.buildd.pottery import intltool


class GenerateTranslationTemplates:
    """Script to generate translation templates from a branch."""

    def __init__(self, branch_spec, result_name, work_dir, log_file=None):
        """Prepare to generate templates for a branch.

        :param branch_spec: Either a branch URL or the path of a local
            branch.  URLs are recognized by the occurrence of ':'.  In
            the case of a URL, this will make up a path for the branch
            and check out the branch to there.
        :param result_name: The name of the result tarball. Should end in
            .tar.gz.
        :param work_dir: The directory to work in. Must exist.
        :param log_file: File-like object to log to. If None, defaults to
            stderr.
        """
        self.work_dir = work_dir
        self.branch_spec = branch_spec
        self.result_name = result_name
        self.logger = self._setupLogger(log_file)

    def _setupLogger(self, log_file):
        """Sets up and returns a logger."""
        if log_file is None:
            log_file = sys.stderr
        logger = logging.getLogger("generate-templates")
        logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler(log_file)
        ch.setLevel(logging.DEBUG)
        logger.addHandler(ch)
        return logger

    def _getBranch(self):
        """Set `self.branch_dir`, and check out branch if needed."""
        if ':' in self.branch_spec:
            # This is a branch URL.  Check out the branch.
            self.branch_dir = os.path.join(self.work_dir, 'source-tree')
            self.logger.info("Getting remote branch %s..." % self.branch_spec)
            self._checkout(self.branch_spec)
        else:
            # This is a local filesystem path.  Use the branch in-place.
            self.logger.info("Using local branch %s..." % self.branch_spec)
            self.branch_dir = self.branch_spec

    def _checkout(self, branch_url):
        """Check out a source branch to generate from.

        The branch is checked out to the location specified by
        `self.branch_dir`.
        """
        self.logger.info("Opening branch %s..." % branch_url)
        branch = Branch.open(branch_url)
        self.logger.info("Getting branch revision tree...")
        rev_tree = branch.basis_tree()
        self.logger.info("Exporting branch to %s..." % self.branch_dir)
        export(rev_tree, self.branch_dir)
        self.logger.info("Exporting branch done.")

    def _makeTarball(self, files):
        """Put the given files into a tarball in the working directory."""
        tarname = os.path.join(self.work_dir, self.result_name)
        self.logger.info("Making tarball with templates in %s..." % tarname)
        tarball = tarfile.open(tarname, 'w|gz')
        files = [name for name in files if not name.endswith('/')]
        for path in files:
            full_path = os.path.join(self.branch_dir, path)
            self.logger.info("Adding template %s..." % full_path)
            tarball.add(full_path, path)
        tarball.close()
        self.logger.info("Tarball generated.")

    def generate(self):
        """Do It.  Generate templates."""
        self.logger.info("Generating templates for %s." % self.branch_spec)
        self._getBranch()
        pots = intltool.generate_pots(self.branch_dir)
        self.logger.info("Generated %d templates." % len(pots))
        if len(pots) > 0:
            self._makeTarball(pots)
        return 0


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print "Usage: %s branch resultname [workdir]" % sys.argv[0]
        print "  'branch' is a branch URL or directory."
        print "  'resultname' is the name of the result tarball."
        print "  'workdir' is a directory, defaults to HOME."
        sys.exit(1)
    if len(sys.argv) == 4:
        workdir = sys.argv[3]
    else:
        workdir = os.environ['HOME']
    script = GenerateTranslationTemplates(
        sys.argv[1], sys.argv[2], workdir)
    sys.exit(script.generate())
