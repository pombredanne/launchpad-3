"""jslint.py - run the JSLint linter ."""

__metaclass__ = type
__all__ = []

import optparse
import os
import subprocess
import sys

from bzrlib import branch, errors, workingtree
from bzrlib.plugin import load_plugins

HERE = os.path.join(os.path.dirname(__file__))
FULLJSLINT = os.path.join(HERE, 'fulljslint.js')
JSLINT_WRAPPER = os.path.join(HERE, 'jslint-wrapper.js')

class FiletypeFilter:
    include_html = False
    def __call__(self, path):
        """Return True for filetypes we want to lint."""
        return path.endswith('.js') or (self.include_html and
               path.endswith('.html'))
js_filter = FiletypeFilter()


class FileFinder:
    def __init__(self):
        self.tree = workingtree.WorkingTree.open_containing('.')[0]

    def find_files_to_lint(self, delta):
        """Return the modified and added files in a tree from a delta."""
        files_to_lint = []
        files_to_lint.extend(info[0] for info in delta.added)
        files_to_lint.extend(info[0] for info in delta.modified)
        # And look also at the renamed attribute for modified files.
        files_to_lint.extend(info[0] for info in delta.renamed if info[4])

        # Select only the appropriate files and turn them in absolute paths.
        return [self.tree.abspath(f) for f in files_to_lint if js_filter(f)]

    def find_files_to_lint_from_working_tree_or_parent(self):
        """Return the file paths to lint based on working tree changes."""
        working_tree_delta = self.tree.changes_from(self.tree.basis_tree())
        if not working_tree_delta.has_changed():
            return self.find_files_to_lint_from_parent()
        else:
            return self.find_files_to_lint(working_tree_delta)

    def find_files_to_lint_from_working_tree(self):
        """Return the file path to lint based on working tree changes."""
        working_tree_delta = self.tree.changes_from(self.tree.basis_tree())
        return self.find_files_to_lint(working_tree_delta)

    def find_files_to_lint_from_parent(self):
        """Return the file path to lint based on working tree changes."""
        submit = self.tree.branch.get_submit_branch()
        if submit is None:
            submit = self.tree.branch.get_parent()
            if submit is None:
                raise errors.NoSubmitBranch(self.tree.branch)
        submit_tree = branch.Branch.open(submit).basis_tree()
        return self.find_files_to_lint(self.tree.changes_from(submit_tree))

    def find_all_files_to_lint(self):
        """Return all the JS files that can be linted."""
        all_files = []
        for file_id in self.tree:
            path = self.tree.id2path(file_id)
            # Skip build files and third party files.
            if path.startswith('lib') or path.startswith('build'):
                continue
            if js_filter(path):
                all_files.append(self.tree.abspath(path))
        return all_files


class JSLinter:
    """Linter for Javascript."""

    def __init__(self, options=None):
        self.options = options

    def jslint_rhino(self, filenames):
        """Run the linter on all selected files using rhino."""
        args = ['rhino', '-f', FULLJSLINT, JSLINT_WRAPPER]
        if self.options:
            args.extend(['-o', self.options])
        args.extend(filenames)
        jslint = subprocess.Popen(args)
        return jslint.wait()

    def jslint_spidermonkey(self, filenames):
        """Run the linter on all selected files using spidermonkey."""
        args = ['js', '-f', FULLJSLINT, JSLINT_WRAPPER]
        if self.options:
            args.extend(['-o', self.options])
        args.extend(filenames)
        jslint = subprocess.Popen(args, stdin=subprocess.PIPE)
        # SpiderMonkey can only read from stdin, so we are multiplexing the
        # different files on stdin.
        files_to_send = list(filenames)
        if self.options:
            files_to_send.insert(0, self.options)
        for filename in files_to_send:
            fh = open(filename, 'r')
            jslint.stdin.write(fh.read())
            fh.close()
            jslint.stdin.write('\nEOF\n')

        return jslint.wait()


def get_options():
    """Parse the command line options."""
    parser = optparse.OptionParser(
        usage="%prog [options] [files]",
        description=(
            "Run Douglas Crockford JSLint script on the JS files. "
            "By default, all modified files in the current working tree are "
            "linted. Or all modified files since the parent branch, if there "
            "are no changes in the current working tree."
            ))
    parser.add_option(
        '-o', '--options', dest='options',
        help=('JS file returning a configuration object for the linter.'))
    parser.add_option(
        '-a', '--all', dest='all', default=False,
        action='store_true',
        help=('Lint all JavaScript files in the branch.'))
    parser.add_option(
        '-p', '--parent', dest='parent', default=False,
        action='store_true',
        help=('Lint all JavaScript files modified from the submit: branch.'))
    parser.add_option(
        '-w', '--working-tree', dest='working_tree', default=False,
        action='store_true',
        help=('Only lint changed files in the working tree.'))
    parser.add_option(
        '-e', '--engine', dest='engine', default='js', action='store',
        help=('Javascript engine to use. Defaults to "js" (SpiderMonkey). '
              'Use "rhino" to use the Java-based Rhino engine'))
    parser.add_option(
        '-i', '--include-html', dest='html', default=False,
        action='store_true', help=('Also lint .html files.'))

    options, args = parser.parse_args()
    if len(args) > 0:
        if options.all or options.parent or options.working_tree:
            parser.error(
                'Cannot specify files with --all, --parent or --working-tree')
    else:
        count = 0
        if options.all:
            count += 1
        if options.parent:
            count += 1
        if options.working_tree:
            count += 1
        if count > 1:
            parser.error(
                'Only one of --all, --parent or --working-tree should be '
                'specified.')
    if options.engine not in ['js', 'rhino']:
        parser.error(
            'Unrecognized engine. Use either "js" or "rhino".')
    return options, args


def main():
    options, args = get_options()
    linter = JSLinter(options.options)
    js_filter.include_html = options.html
    if args:
        files = [f for f in args if js_filter(f)]
    else:
        load_plugins()
        finder = FileFinder()
        if options.all:
            files = finder.find_all_files_to_lint()
        elif options.working_tree:
            files = finder.find_files_to_lint_from_working_tree()
        elif options.parent:
            files = finder.find_files_to_lint_from_parent()
        else:
            files = finder.find_files_to_lint_from_working_tree_or_parent()
    if not files:
        print 'jslint: No files to lint.'
    else:
        if len(files) == 1:
            print 'jslint: 1 file to lint.'
        else:
            print 'jslint: %d files to lint.' % len(files)
        if options.engine == 'js':
            jslint = linter.jslint_spidermonkey
        elif options.engine == 'rhino':
            jslint = linter.jslint_rhino
        else:
            raise AssertionError('Unknown engine: %s' % options.engine)
        sys.exit(jslint(files))

