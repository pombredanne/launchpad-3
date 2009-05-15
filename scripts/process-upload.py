#!/usr/bin/python2.4
"""Upload processor.

Given a bunch of context information and a bunch of files, process them as
an upload to a distro/whatever within the launchpad.
"""

import _pythonpath

# XXX: This import is not actually used, but it avoids a major circular import
# problem. We love you too, Python.
from lp.archiveuploader.uploadpolicy import policy_options
from canonical.config import config
from lp.soyuz.scripts.soyuz_process_upload import ProcessUpload


if __name__ == '__main__':
    script = ProcessUpload('process-upload', dbuser=config.uploader.dbuser)
    script.lock_and_run()
