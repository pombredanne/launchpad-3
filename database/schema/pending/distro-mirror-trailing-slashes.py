#!/usr/bin/env python
# Copyright 2007 Canonical Ltd.  All rights reserved.

import _pythonpath

from canonical.lp import initZopeless

from canonical.launchpad.scripts import execute_zcml_for_scripts
from canonical.launchpad.database import DistributionMirror


if __name__ == '__main__':
    execute_zcml_for_scripts()
    ztm = initZopeless(dbuser='launchpad', implicitBegin=False)
    ztm.begin()

    for mirror in DistributionMirror.select():
        if mirror.http_base_url and not mirror.http_base_url.endswith('/'):
            mirror.http_base_url = mirror.http_base_url + '/'
        if mirror.ftp_base_url and not mirror.ftp_base_url.endswith('/'):
            mirror.ftp_base_url = mirror.ftp_base_url + '/'
        if mirror.rsync_base_url and not mirror.rsync_base_url.endswith('/'):
            mirror.rsync_base_url = mirror.rsync_base_url + '/'

    ztm.commit()

