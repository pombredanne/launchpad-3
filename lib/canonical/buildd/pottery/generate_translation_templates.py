#! /usr/bin/python
# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import os.path
import sys

from bzrlib.branch import Branch
from bzrlib.export import export

from canonical.buildd.pottery import intltool


class GenerateTranslationTemplates:
    """Script to generate translation templates from a branch."""

    def __init__(self, branch_spec, work_dir):
        """Prepare to generate templates for a branch.

        :param branch_spec: Either a branch URL or the path of a local
            branch.  URLs are recognized by the occurrence of ':'.  In
            the case of a URL, this will make up a path for the branch
            and check out the branch to there.
        :param work_dir: The directory to work in. Must exist.
        """
        self.work_dir = work_dir
        self.branch_spec = branch_spec

    def _getBranch(self):
        """Set `self.branch_dir`, and check out branch if needed."""
        if ':' in self.branch_spec:
            # This is a branch URL.  Check out the branch.
            self.branch_dir = os.path.join(self.work_dir, 'source-tree')
            self._checkout(self.branch_spec)
        else:
            # This is a local filesystem path.  Use the branch in-place.
            self.branch_dir = self.branch_spec

    def _checkout(self, branch_url):
        """Check out a source branch to generate from.

        The branch is checked out to the location specified by
        `self.branch_dir`.
        """
        branch = Branch.open(branch_url)
        rev_tree = branch.basis_tree()
        export(rev_tree, self.branch_dir)

    def generate(self):
        """Do It.  Generate templates."""
        self._getBranch()
        pots = intltool.generate_pots(self.branch_dir)
        print "\n".join(
            [os.path.normpath(os.path.join(self.branch_dir, potpath))
                for potpath in pots])
        return 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print "Usage: %s branch [workdir]" % sys.argv[0]
        print "  'branch' is a branch URL or directory."
        print "  'workdir' is a directory, defaults to HOME."
        sys.exit(1)
    if len(sys.argv) == 3:
        workdir = sys.argv[2]
    else:
        workdir = os.environ['HOME']
    script = GenerateTranslationTemplates(sys.argv[1], workdir)
    sys.exit(script.generate())
