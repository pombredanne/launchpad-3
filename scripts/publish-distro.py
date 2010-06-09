#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=C0103,W0403

import _pythonpath

from optparse import OptionParser

from canonical.config import config
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger)
from lp.services.scripts.base import LaunchpadScriptFailure
from canonical.lp import initZopeless
from lp.soyuz.scripts import publishdistro


if __name__ == "__main__":
    parser = OptionParser()
    publishdistro.add_options(parser)
    options, args = parser.parse_args()
    assert len(args) == 0, "publish-distro takes no arguments, only options."

    log = logger(options, "publish-distro")
    log.debug("Initialising zopeless.")
    execute_zcml_for_scripts()
    txn = initZopeless(dbuser=config.archivepublisher.dbuser)

    try:
        publishdistro.run_publisher(options, txn)
    except LaunchpadScriptFailure, err:
        log.error(err)
