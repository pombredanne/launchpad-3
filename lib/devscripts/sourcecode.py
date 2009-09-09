# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tools for maintaining the Launchpad source code."""

__metaclass__ = type
__all__ = [
    'interpret_config',
    'parse_config_file',
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


def interpret_config(configuration):
    """Interpret a configuration stream, as parsed by 'parse_config_file'.

    :param configuration: A sequence of parsed configuration entries.
    :return: A dict mapping the names of the sourcecode dependencies to a
        2-tuple of their branches and whether or not they are optional.
    """
    return dict(map(interpret_config_entry, configuration))
