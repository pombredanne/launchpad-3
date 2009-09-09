# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tools for maintaining the Launchpad source code."""

__metaclass__ = type
__all__ = [
    'interpret_config',
    'parse_config_file',
    'plan_update',
    ]


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
    existing_branches = set(existing_branches)
    config_branches = set(configuration.keys())
    new_branches = config_branches - existing_branches
    removed_branches = existing_branches - config_branches
    update_branches = config_branches.intersection(existing_branches)
    return (
        _subset_dict(configuration, new_branches),
        _subset_dict(configuration, update_branches),
        removed_branches)
