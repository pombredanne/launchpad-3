# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tools for maintaining the Launchpad source code."""

__metaclass__ = type
__all__ = [
    'parse_config_file',
    ]


def parse_config_file(file_handle):
    for line in file_handle:
        if line.startswith('#'):
            continue
        yield [token.strip() for token in line.split('=')]
