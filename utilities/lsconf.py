#!/usr/bin/python2.4

"""Create lazr.config schema and confs from ZConfig data."""

__metatype__ = type


import os
import sys
from optparse import OptionParser
from operator import attrgetter
from textwrap import dedent

# Scripts may have relative imports.
# pylint: disable-msg=W0403
import _pythonpath
import canonical.config
from canonical.lazr.config import ImplicitTypeSchema


_schema_dir = os.path.abspath(os.path.dirname(canonical.config.__file__))
_root = os.path.dirname(os.path.dirname(os.path.dirname(_schema_dir)))


class Configuration:
    """A lazr.config configuration."""
    _schema_path = os.path.join(_schema_dir, 'schema-lazr.conf')

    def __init__(self, conf_path, schema_path=None):
        """Initialise the Configuration.

        :conf_path: The path to the lazr.config conf file.
        :schema_path: The path to the lazr.config schema that defines
            the configuration.
        """
        self.schema_path = schema_path or self._schema_path
        self.schema = ImplicitTypeSchema(self.schema_path)
        self.conf_path = conf_path
        self.config = self.schema.load(self.conf_path)

    def config_file_for_value(self, section, key):
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
        conf_path = os.path.abspath(conf_file_name)
        return conf_path[len(_root) + 1:]

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
            print '[%s]' % section.name
            if verbose and section.optional:
                print '# This section is optional.\n'
            for count, key in enumerate(sorted(section)):
                if verbose:
                    if count > 0:
                        # Separate keys by a blank line.
                        print
                    conf_file_name = self.config_file_for_value(section, key)
                    print '# Defined in: %s' % conf_file_name
                print '%s: %s' % (key, section[key])


def get_option_parser():
    """Return the option parser for this program."""
    usage = dedent("""    %prog [options] lazr-config.conf

    List all the sections and keys in an environment's lazr configuration.
    The configuration is assembled from the schema and conf files. Verbose
    annotates each key with the location of the file that set its value.""")
    parser = OptionParser(usage=usage)
    parser.add_option(
        "-l", "--schema", dest="schema_path",
        help="the path to the lazr.config schema file")
    parser.add_option(
        "-v", "--verbose", action="store_true",
        help="explain where the section and keys are set")
    return parser


def main(argv=None):
    """Run the command line operations."""
    if argv is None:
        argv = sys.argv
    parser = get_option_parser()
    (options, arguments) = parser.parse_args(args=argv[1:])
    if len(arguments) == 0:
        parser.error('Config file path is required.')
        # Does not return.
    elif len(arguments) > 1:
        parser.error('Too many arguments.')
        # Does not return.
    conf_path = arguments[0]
    configuration = Configuration(conf_path, options.schema_path)
    configuration.list_config(verbose=options.verbose)


if __name__ == '__main__':
    sys.exit(main())
