#!/usr/bin/python2.4
"""Create lazr.config schema and confs from ZConfig data."""
# Scripts may have realtive imports.
# pylint: disable-msg=W0403

__meta__ = type


from optparse import OptionParser
from operator import attrgetter
import os
import sys

import _pythonpath
import canonical.config
from canonical.lazr.config import ImplicitTypeSchema


_schema_dir = os.path.abspath(os.path.dirname(canonical.config.__file__))
_root = os.path.dirname(os.path.dirname(os.path.dirname(_schema_dir)))


class Configuration:
    """A lazr.config configuration."""
    _schema_path = os.path.join(_schema_dir, 'schema-lazr.conf')

    def __init__(self, schema_path=None, conf_path=None):
        """Initialise the Configuration.

        :schema_path: The path to the lazr.config schema that defines
            the configuration.
        :conf_path: The path to the lazr.config conf file.
        """
        self.schema_path = schema_path or self._schema_path
        self.schema = ImplicitTypeSchema(self.schema_path)
        self.conf_path = conf_path
        self.config = self.schema.load(self.conf_path)

    def where_is_value_set(self, section, key):
        """Return the local path to the file that sets the section key."""
        conf_file_name = self.schema.filename
        value = section[key]
        previous_config_data = self.config.data
        # Walk the stack of config_data until a change is found.
        for config_data in self.config.overlays:
            if (section.name in config_data
                and config_data[section.name][key] != value):
                conf_file_name = previous_config_data.filename
                break
            previous_config_data = config_data
        return os.path.abspath(conf_file_name).replace(_root, '')

    def list_config(self, verbose=False):
        """Print all the sections and keys in a configuration.

        Print the final state of configuration after all the conf files
        are loaded.
        """
        print '# This configuration derives from:'
        for config_data in self.config.overlays:
            print '#     %s' % config_data.filename
        print
        name_key = attrgetter('name')
        for count, section in enumerate(sorted(self.config, key=name_key)):
            if count > 0:
                # Separate sections by a blank line, or two when verbose.
                print
                if verbose:
                    print
            print '[%s]' % section.name
            if verbose and section.optional:
                print '# This section is optional.\n'
            for count, key in enumerate(sorted(section)):
                if verbose:
                    if count > 0:
                        # Separate keys by a blank line.
                        print
                    conf_file_name = self.where_is_value_set(section, key)
                    print '# Defined in: %s' % conf_file_name
                print '%s: %s' % (key, section[key])


def get_option_parser():
    """Return the option parser for this program."""
    usage = "usage: %prog [options] lazr-config.conf"
    parser = OptionParser(usage=usage)
    parser.add_option(
        "-l", "--schema", dest="schema_path",
        help="The path to the lazr.config schema file.")
    parser.add_option(
        "-v", "--verbose", dest="verbose", action="store_true",
        help="Explain where the section and keys are set.")
    parser.set_defaults(
        schema_path=None,
        verbose=False,
        debug=True)
    return parser


def main(argv=None):
    """Run the command line operations."""
    if argv is None:
        argv = sys.argv
    parser = get_option_parser()
    (options, args) = parser.parse_args(args=argv[1:])
    conf_path, = args
    configuration = Configuration(options.schema_path, conf_path)
    configuration.list_config(verbose=options.verbose)


if __name__ == '__main__':
    sys.exit(main())

