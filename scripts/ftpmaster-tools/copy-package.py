#!/usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Copy publications across suites."""

import _pythonpath


from canonical.launchpad.scripts.ftpmaster import PackageCopier


if __name__ == '__main__':
    script = PackageCopier('copy-package', dbuser='lucille')
    script.lock_and_run()

