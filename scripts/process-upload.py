#!/usr/bin/python2.4
"""Upload processor.

Given a bunch of context information and a bunch of files, process them as
an upload to a distro/whatever within the launchpad.
"""

import os
import _pythonpath

from canonical.archiveuploader.uploadpolicy import policy_options
from canonical.archiveuploader.uploadprocessor import UploadProcessor
from canonical.config import config
from canonical.launchpad.scripts.base import (
    LaunchpadScript, LaunchpadScriptFailure)
from canonical.launchpad.scripts.soyuz_process_upload import ProcessUpload


if __name__ == '__main__':
    script = ProcessUpload('process-upload', dbuser=config.uploader.dbuser)
    script.lock_and_run()

