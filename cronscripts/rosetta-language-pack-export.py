#!/usr/bin/python
# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Script to export a tarball of translations for a distro release."""

__metaclass__ = type

import _pythonpath

import optparse
import sys

from canonical.lp import initZopeless
from canonical.launchpad.scripts import (execute_zcml_for_scripts, logger,
    logger_options)
from canonical.launchpad.scripts.language_pack import export_language_pack

def parse_options(args):
    """Parse options for exporting distribution release translations.

    Returns a 3-tuple containing an options object, a distribution name and a
    release name.
    """

    parser = optparse.OptionParser(
        usage='%prog [options] distribution release')
    parser.add_option(
        '--email',
        dest='email_addresses',
        default=[],
        action='append',
        help='An email address to send a notification to.'
        )
    parser.add_option(
        '--output',
        dest='output',
        default=None,
        action='store',
        help='A file to send the generated tarball to, rather than the'
             ' Libraran.'
        )
    parser.add_option(
        '--update',
        dest='update',
        default=False,
        action='store_true',
        help='Whether the generated language pack should be an update from'
             ' the previous export.'
        )

    # Add the verbose/quiet options.
    logger_options(parser)

    parser.add_option(
        '--component',
        dest='component',
        default=None,
        action='store',
        help='Select a concrete archive component to export.'
        )

    parser.add_option(
        '--force-utf8-encoding',
        dest='force_utf8',
        default=False,
        action='store_true',
        help='Whether the exported files should be exported using UTF-8'
             ' encoding.'
        )

    options, args = parser.parse_args(args)

    if len(args) != 2:
        parser.error('Wrong number of arguments')

    return options, args[0], args[1]

def main(argv):
    initZopeless()
    execute_zcml_for_scripts()

    options, distribution_name, release_name = parse_options(argv[1:])

    logger_object = logger(options, 'rosetta-language-pack-export')
    logger_object.info(
            'Exporting translations for release %s of distribution %s',
            distribution_name, release_name
            )

    success = export_language_pack(
        distribution_name=distribution_name,
        release_name=release_name,
        component=options.component,
        update=options.update,
        force_utf8=options.force_utf8,
        output_file=options.output,
        email_addresses=options.email_addresses,
        logger=logger_object)

    if success:
        return 0
    else:
        return 1

if __name__ == '__main__':
    sys.exit(main(sys.argv))

