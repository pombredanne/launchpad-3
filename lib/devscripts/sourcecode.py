# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tools for maintaining the Launchpad source code."""

__metaclass__ = type
__all__ = [
    'interpret_config',
    'parse_config_file',
    'plan_update',
    ]

import os
import shutil

from bzrlib.branch import Branch
from bzrlib.bzrdir import BzrDir
from bzrlib.plugin import load_plugins
from bzrlib.transport import get_transport
from bzrlib.workingtree import WorkingTree


def parse_config_file(file_handle):
    """Parse the source code config file 'file_handle'.

    :param file_handle: A file-like object containing sourcecode
        configuration.
    :return: A sequence of lines of either '[key, value]' or
        '[key, value, optional]'.
    """
    for line in file_handle:
        if line.startswith('#'):
            continue
        yield [token.strip() for token in line.split('=')]


def interpret_config_entry(entry):
    """Interpret a single parsed line from the config file."""
    return (entry[0], (entry[1], len(entry) > 2))


def interpret_config(config_entries):
    """Interpret a configuration stream, as parsed by 'parse_config_file'.

    :param configuration: A sequence of parsed configuration entries.
    :return: A dict mapping the names of the sourcecode dependencies to a
        2-tuple of their branches and whether or not they are optional.
    """
    return dict(map(interpret_config_entry, config_entries))


def _subset_dict(d, keys):
    """Return a dict that's a subset of 'd', based on the keys in 'keys'."""
    return dict((key, d[key]) for key in keys)


def plan_update(existing_branches, configuration):
    """Plan the update to existing branches based on 'configuration'.

    :param existing_branches: A sequence of branches that already exist.
    :param configuration: A dictionary of sourcecode configuration, such as is
        returned by `interpret_config`.
    :return: (new_branches, update_branches, removed_branches), where
        'new_branches' are the branches in the configuration that don't exist
        yet, 'update_branches' are the branches in the configuration that do
        exist, and 'removed_branches' are the branches that exist locally, but
        not in the configuration. 'new_branches' and 'update_branches' are
        dicts of the same form as 'configuration', 'removed_branches' is a
        set of the same form as 'existing_branches'.
    """
    existing_branches = set(existing_branches)
    config_branches = set(configuration.keys())
    new_branches = config_branches - existing_branches
    removed_branches = existing_branches - config_branches
    update_branches = config_branches.intersection(existing_branches)
    return (
        _subset_dict(configuration, new_branches),
        _subset_dict(configuration, update_branches),
        removed_branches)


def find_branches(directory):
    """List the directory names in 'directory' that are branches."""
    transport = get_transport(directory)
    return (
        os.path.basename(branch.base.rstrip('/'))
        for branch in BzrDir.find_branches(transport))


def get_branches(sourcecode_directory, new_branches,
                 possible_transports=None):
    """Get the new branches into sourcecode."""
    for project, (branch_url, optional) in new_branches.iteritems():
        destination = os.path.join(sourcecode_directory, project)
        remote_branch = Branch.open(
            branch_url, possible_transports=possible_transports)
        possible_transports.append(
            remote_branch.bzrdir.root_transport)
        print 'Getting %s from %s' % (project, branch_url)
        remote_branch.bzrdir.sprout(
            destination, create_tree_if_local=True,
            source_branch=remote_branch,
            possible_transports=possible_transports)


def update_branches(sourcecode_directory, update_branches,
                    possible_transports=None):
    """Update the existing branches in sourcecode."""
    if possible_transports is None:
        possible_transports = []
    for project, (branch_url, optional) in update_branches.iteritems():
        destination = os.path.join(sourcecode_directory, project)
        print 'Updating %s' % (project,)
        local_tree = WorkingTree.open(destination)
        remote_branch = Branch.open(
            branch_url, possible_transports=possible_transports)
        possible_transports.append(
            remote_branch.bzrdir.root_transport)
        local_tree.pull(
            remote_branch,
            possible_transports=possible_transports)


def remove_branches(sourcecode_directory, removed_branches):
    """Remove sourcecode that's no longer there."""
    for project in removed_branches:
        destination = os.path.join(sourcecode_directory, project)
        print 'Removing %s' % project
        try:
            shutil.rmtree(destination)
        except OSError:
            os.unlink(destination)


def update_sourcecode(sourcecode_directory, config_filename):
    """Update the sourcecode."""
    config_file = open(config_filename)
    config = interpret_config(parse_config_file(config_file))
    config_file.close()
    branches = find_branches(sourcecode_directory)
    new, updated, removed = plan_update(branches, config)
    possible_transports = []
    get_branches(sourcecode_directory, new, possible_transports)
    update_branches(sourcecode_directory, updated, possible_transports)
    remove_branches(sourcecode_directory, removed)


def get_launchpad_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


def main(args):
    root = get_launchpad_root()
    if len(args) > 1:
        sourcecode_directory = args[1]
    else:
        sourcecode_directory = os.path.join(root, 'sourcecode')
    config_filename = os.path.join(root, 'utilities', 'sourcedeps.conf')
    print 'Sourcecode: %s' % (sourcecode_directory,)
    print 'Config: %s' % (config_filename,)
    load_plugins()
    update_sourcecode(sourcecode_directory, config_filename)
    return 0
