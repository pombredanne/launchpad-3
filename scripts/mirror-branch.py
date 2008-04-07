#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Script run by cronscripts/supermirror-pull.py to mirror single branches.

Do NOT run this script yourself unless you really know what you are doing. Use
cronscripts/supermirror-pull.py instead.

Usage: scripts/mirror-branch.py source_url dest_url branch_id unique_name \
                                branch_type oops_prefix

Where:
  source_url is the location of the branch to be mirrored.
  dest_url is the location to mirror the branch to.
  branch_id is the database ID of the branch.
  unique_name is the unique name of the branch.
  branch_type is one of HOSTED, MIRRORED, IMPORTED
  oops_prefix is the OOPS prefix to use, unique in the set of running
      instances of this script.
"""

# This script does not use the standard Launchpad script framework as it is
# not intended to be run by itself.


import _pythonpath
from optparse import OptionParser
import sys

import bzrlib.repository

from canonical.codehosting.puller.worker import (
    install_worker_ui_factory, PullerWorker, PullerWorkerProtocol)
from canonical.config import config
from canonical.launchpad.interfaces import BranchType
from canonical.launchpad.webapp.errorlog import globalErrorUtility


branch_type_map = {
    BranchType.HOSTED: 'upload',
    BranchType.MIRRORED: 'mirror',
    BranchType.IMPORTED: 'import'
    }


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
    (options, arguments) = parser.parse_args()
    (source_url, destination_url, branch_id, unique_name,
     branch_type_name, oops_prefix) = arguments

    branch_type = BranchType.items[branch_type_name]
    config.setProcess(
        'mirror-branch-%s-lazr.conf' % branch_type_map[branch_type])
    globalErrorUtility.appendToOopsPrefix(oops_prefix)
    shut_up_deprecation_warning()
    force_bzr_to_use_urllib()

    protocol = PullerWorkerProtocol(sys.stdout)
    install_worker_ui_factory(protocol)
    PullerWorker(
        source_url, destination_url, int(branch_id), unique_name, branch_type,
        protocol).mirror()
