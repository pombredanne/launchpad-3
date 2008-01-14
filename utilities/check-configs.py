#! /usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Check that all the launchpad.conf files can be loaded.

Usage hint:

% utilities/check-configs.py -v 'canonical/pid_dir=/tmp'
"""

import _pythonpath

import os
import sys
import ZConfig
import optparse
import traceback


def main():
    parser = optparse.OptionParser(usage="""\
%prog [options] [overrides]

Parse all launchpad.conf files found under the 'config' directory rooted at
the current working directory.  Warn about any problems loading the config
file.

With a specified directory, search there instead of the current working
directory for launchpad.conf files.  The search is always recursive.

The environment variable LPCONFIG can be used to limit the search to only
subdirectories of config that match $LPCONFIG, otherwise all are searched.

overrides are passed directly to ZConfig.loadConfig().
""")
    parser.add_option('-v', '--verbose',
                      action='count', dest='verbosity',
                      help='Increase verbosity')
    options, arguments = parser.parse_args()

    # Are we searching for one config or for all configs?
    directory = os.path.join(os.getcwd(), 'configs')
    configs = []
    lpconfig = os.environ.get('LPCONFIG')
    if lpconfig is None:
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                if filename == 'launchpad.conf':
                    configs.append(os.path.join(dirpath, filename))
    else:
        configs.append(os.path.join(directory, 'configs', lpconfig,
                                    'launchpad.conf'))

    # Import this to get the path to the schema.xml file.
    import canonical.config
    schema_file = os.path.join(os.path.dirname(canonical.config.__file__),
                               'schema.xml')
    schema = ZConfig.loadSchema(schema_file)

    # Load each config and report any errors.
    summary = []
    for config in sorted(configs):
        try:
            root, handlers = ZConfig.loadConfig(schema, config, arguments)
        except ZConfig.ConfigurationSyntaxError, error:
            if options.verbosity > 2:
                traceback.print_exc()
            elif options.verbosity > 1:
                print error
            summary.append((config, False))
        else:
            summary.append((config, True))

    prefix_length = len(directory)
    for config, status in summary:
        path = config[prefix_length + 1:]
        if status:
            if options.verbosity > 0:
                print 'SUCCESS:', path
        else:
            print 'FAILURE:', path

    # Return a useful exit code.  0 == all success.
    return len([config for config, status in summary if not status])


if __name__ == '__main__':
    sys.exit(main())
