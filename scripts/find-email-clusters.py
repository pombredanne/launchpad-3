
import sys
import logging
import optparse

from pyme.constants import validity

from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger_options, logger as logger_from_options)
from canonical.launchpad.scripts.keyringtrustanalyser import *

validity_map = {
    'UNDEFINED': validity.UNDEFINED,
    'NEVER':     validity.NEVER,
    'MARGINAL':  validity.MARGINAL,
    'FULL':      validity.FULL,
    'ULTIMATE':  validity.ULTIMATE,
    }

def main(argv):
    parser = optparse.OptionParser(
        usage="usage: %prog [options] keyrings ...",
        description="This script inferrs clusters of "
        "email addresses belonging to a single user "
        "from the user IDs attached to PGP keys.")
    parser.add_option('-o', '--output', metavar='FILE', action='store',
                      help='Output clusters to given file',
                      type='string', dest='output', default=None)
    parser.add_option('--trust', metavar='KEYRING', action='append',
                      help='Trust the owners of keys on this keyring',
                      type='string', dest='trust', default=[])
    parser.add_option('--owner-trust', metavar='TRUST', action='store',
                      help='What level of trust to assign to trusted keys',
                      type='string', dest='owner_trust', default='ULTIMATE')
    parser.add_option('--min-valid', metavar='TRUST', action='store',
                      help='Minimum trust necessary for a user ID to '
                      'be considered valid',
                      type='string', dest='minvalid', default='MARGINAL')

    logger_options(parser, logging.WARNING)

    options, args = parser.parse_args(argv[1:])

    # map validity options
    if options.owner_trust.upper() not in validity_map:
        sys.stderr.write('%s: unknown owner trust value %s'
                         % (argv[0], options.owner_trust))
        return 1
    options.owner_trust = validity_map[options.owner_trust.upper()]

    if options.minvalid.upper() not in validity_map:
        sys.stderr.write('%s: unknown min valid value %s'
                         % (argv[0], options.minvalid))
        return 1
    options.minvalid = validity_map[options.minvalid.upper()]

    # get logger
    logger = logger_from_options(options)

    if options.output is not None:
        logger.debug('openning %s', options.output)
        fp = open(options.output, 'w')
    else:
        fp = sys.stdout

    logger.info('Setting up utilities')
    execute_zcml_for_scripts()

    logger.info('Loading trusted keyrings')
    for keyring in options.trust:
        logger.info('Loading %s', keyring)
        addTrustedKeyring(keyring, options.owner_trust)

    logger.info('Loading other keyrings')
    for keyring in args:
        logger.info('Loading %s', keyring)
        addOtherKeyring(keyring)

    logger.info('Computing address clusters')
    for cluster in findEmailClusters(options.minvalid):
        for email in cluster:
            fp.write('%s\n' % email)
        fp.write('\n')

    logger.info('Done')

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
