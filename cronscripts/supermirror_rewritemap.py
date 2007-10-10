#!/usr/bin/python2.4
# Copyright 2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0403

"""Generate a file mapping ~user/product/branch to on-disk paths, suitable for
use with Apache's RewriteMap directive.

Apache config notes:

  - magic incantation::
      
      RewriteMap branch-list txt:/path/to/map-file.txt
      ...
      RewriteEngine On
      # Assume branch dirs are kept in a directory 'branches' under the
      # DocumentRoot
      RewriteRule ^/(~[^/]+/[^/]+/[^/]+)/(.*)$ branches/${branch-list:$1}/$2 [L]

  - UserDir directive must not be in effect if you want to be able to rewrite
    top-level ~user paths.
"""

__metaclass__ = type

import _pythonpath
import logging

from canonical.launchpad.scripts import supermirror_rewritemap
from canonical.launchpad.scripts.base import (LaunchpadCronScript,
    LaunchpadScriptFailure)
from canonical.config import config


class SupermirrorRewriteMap(LaunchpadCronScript):
    loglevel = logging.WARNING
    def main(self):
        if len(self.args) != 1:
            raise LaunchpadScriptFailure('expected a filename argument')

        filename = self.args[0]
        self.txn.begin()
        outfile = open(filename, 'wb')
        supermirror_rewritemap.write_map(outfile)
        outfile.close()
        self.txn.abort()


if __name__ == '__main__':
    script = SupermirrorRewriteMap('supermirror-rewritemap',
                dbuser=config.supermirror.dbuser)
    script.lock_and_run(implicit_begin=False)

