#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.

import _pythonpath
import sys

from optparse import OptionParser

from canonical.authserver.client.branchstatus import BranchStatusClient
from canonical.config import config
from canonical.launchpad.interfaces import BranchType
from canonical.launchpad.scripts import logger_options, logger
from canonical.launchpad.scripts.supermirror.branchtomirror import BranchToMirror


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

    branch_type_map = {
        BranchType.HOSTED: 'upload',
        BranchType.MIRRORED: 'mirror',
        BranchType.IMPORTED: 'import'
        }

    branch_status_client = BranchStatusClient()
    source_url = arguments[0]
    destination_url = arguments[1]
    branch_id = arguments[2]
    unique_name = arguments[3]
    branch_type_name = arguments[4]

    branch_type = BranchType.items[branch_type_name]

    errorreports = getattr(
        config.supermirror,
        '%s_errorreports' % (branch_type_map[branch_type],))

    # Customize the oops reporting config.
    config.launchpad.errorreports.oops_prefix = errorreports.oops_prefix
    config.launchpad.errorreports.errordir = errorreports.errordir
    config.launchpad.errorreports.copy_to_zlog = errorreports.copy_to_zlog

    log = logger(options, 'branch-puller')

    shut_up_deprecation_warning()
    force_bzr_to_use_urllib()

    BranchToMirror(
        source_url, destination_url, branch_status_client, int(branch_id),
        unique_name, branch_type).mirror(log)
