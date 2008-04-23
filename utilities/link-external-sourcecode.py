#!/usr/bin/env python

import optparse

from os import curdir, listdir, sep, symlink
from os.path import realpath, exists, join
from sys import stdout
from urllib import unquote
from urlparse import urlparse

from bzrlib.branch import Branch


def url2path(url):
    """Convert a URL to a local filesystem path.

    Returns `None` if the URL does not reference the local filesystem.
    """
    scheme, netloc, path, params, query, fragment = urlparse(url)
    if scheme == 'file' and netloc in ['', 'localhost']:
        return unquote(path)
    return None


def get_parent(branch_dir):
    """Return the parent branch directory, otherwise `None`."""
    parent_dir = Branch.open(branch_dir).get_parent()
    if parent_dir is not None:
        return url2path(parent_dir)
    return None


def gen_missing_files(source, destination):
    """Generate info on every file in source not in destination."""
    for name in listdir(source):
        destination_file = join(destination, name)
        if not exists(destination_file):
            source_file = join(source, name)
            yield source_file, destination_file


if __name__ == '__main__':
    parser = optparse.OptionParser(
        usage="%prog [branch] [parent]",
        description=(
            "Add a symlink in <target>/sourcecode for each corresponding "
            "file in <parent>/sourcecode."),
        epilog=(
            "Most of the time this does the right thing if run "
            "with no arguments."),
        add_help_option=False)
    parser.add_option(
        '-p', '--parent', dest='parent', default=None,
        help=("The directory of the parent tree. If not specified, "
              "the Bazaar parent branch."),
        metavar="DIR")
    parser.add_option(
        '-t', '--target', dest='target', default=curdir,
        help=("The directory of the target tree. If not specified, "
              "the current working directory."),
        metavar="DIR")
    parser.add_option(
        '-q', '--quiet', dest='verbose', action='store_false',
        help="Be less verbose.")
    parser.add_option(
        '-h', '--help', action='help',
        help="Show this help message and exit.")
    parser.set_defaults(verbose=True)

    options, args = parser.parse_args()

    # Be compatible with link-external-sourcecode.sh.
    if len(args) == 1:
        if options.parent is None:
            options.parent = args[0]
        else:
            parser.error("Cannot specify parent tree as named "
                         "argument and positional argument.")

    # Discover the parent branch using Bazaar.
    if options.parent is None:
        options.parent = get_parent(options.target)

    if options.parent is None:
        parser.error(
            "Parent branch not specified, and could not be discovered.")

    missing_files = gen_missing_files(
        realpath(join(options.parent, 'sourcecode')),
        join(options.target, 'sourcecode'))

    for target, link in missing_files:
        symlink(target, link)
        if options.verbose:
            stdout.write('%s -> %s\n' % (
                    join(*(link.rsplit(sep, 3)[-3:])), target))


# End
