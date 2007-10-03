#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Launchpad version of ftpmaster-tools/remove-package.py."""


import _pythonpath

from canonical.launchpad.scripts.ftpmaster import PackageRemover


if __name__ == '__main__':
    # XXX cprov 20070926: create config.archivepublisher.dbuser
    script = PackageRemover('lp-remove-package', dbuser='lucille')
    script.lock_and_run()

