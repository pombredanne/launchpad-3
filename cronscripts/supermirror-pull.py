#!/usr/bin/python2.4
# Copyright 2006 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0403

import _pythonpath

from optparse import OptionParser

from canonical.config import config
from canonical.launchpad.interfaces import BranchType
from canonical.launchpad.scripts import logger_options, logger
from canonical.launchpad.scripts.supermirror import mirror, jobmanager

import bzrlib.repository


def shut_up_deprecation_warning():
    # XXX DavidAllouche 2006-01-29:
    # Quick hack to disable the deprecation warning for old repository
    # formats.
    bzrlib.repository._deprecation_warning_done = True

def force_bzr_to_use_urllib():
    # These lines prevent bzr from using pycurl to connect to http: urls.  We
    # want this for two reasons:
    # 1) pycurl rejects self signed certificates, which prevents a significant
    #    number of mirror branchs from updating, and
    # 2) the script sometimes hangs inside pycurl, preventing all mirrors from
    #    being updated until the script is restarted.
    # There is no test for this (it would involve a great number of moving
    # parts) but it has been verified to work on production.  Also see
    # https://bugs.launchpad.net/bzr/+bug/82086
    from bzrlib.transport import register_lazy_transport
    register_lazy_transport('http://', 'bzrlib.transport.http._urllib',
                            'HttpTransport_urllib')
    register_lazy_transport('https://', 'bzrlib.transport.http._urllib',
                            'HttpTransport_urllib')


if __name__ == '__main__':
    parser = OptionParser()
    logger_options(parser)
    (options, arguments) = parser.parse_args()
    which = arguments.pop(0)
    if arguments:
        parser.error("Unhandled arguments %s" % repr(arguments))

    branch_type_map = {
        'upload': BranchType.HOSTED,
        'mirror': BranchType.MIRRORED,
        'import': BranchType.IMPORTED
        }

    try:
        branch_type = branch_type_map[which]
    except KeyError:
        parser.error(
            'Expected one of %s, but got: %r'
            % (branch_type_map.keys(), which))

    errorreports = getattr(config.supermirror, '%s_errorreports' % (which,))
    manager = jobmanager.JobManager(branch_type)

    # Customize the oops reporting config.
    config.launchpad.errorreports.oops_prefix = errorreports.oops_prefix
    config.launchpad.errorreports.errordir = errorreports.errordir
    config.launchpad.errorreports.copy_to_zlog = errorreports.copy_to_zlog

    log = logger(options, 'branch-puller')

    shut_up_deprecation_warning()
    force_bzr_to_use_urllib()
    mirror(log, manager)
