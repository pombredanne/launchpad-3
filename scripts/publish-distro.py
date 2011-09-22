#!/usr/bin/python -S
#
# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=C0103,W0403

import _pythonpath

from canonical.config import config
from lp.soyuz.scripts.publishdistro import PublishDistro


if __name__ == "__main__":
    script = PublishDistro('publish-distro', dbuser='publish_distro')
    script.lock_and_run()
