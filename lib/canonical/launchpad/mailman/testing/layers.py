# Copyright 2008 Canonical Ltd.  All rights reserved.

"""A marker layer for the Mailman integration tests."""

__metaclass__ = type
__all__ = [
    'MailmanLayer',
    ]


import os
import atexit

from canonical.config import config
from canonical.testing.layers import AppServerLayer
from canonical.launchpad.mailman.runmailman import start_mailman, stop_mailman


class MailmanLayer(AppServerLayer):
    """A layer for the Mailman integration tests."""

    @classmethod
    def setUp(cls):
        # Stop Mailman if it's currently running.
        pid_file = os.path.join(
            AppServerLayer.appserver_config.mailman.build_var_dir,
            'data', 'master-qrunner.pid')
        if os.path.exists(pid_file):
            stop_mailman(quiet=True, config=AppServerLayer.appserver_config)
        start_mailman(quiet=True, config=AppServerLayer.appserver_config)
        # Make sure that mailman is killed even if tearDown() is skipped.
        atexit.register(cls.tearDown)

    @classmethod
    def tearDown(cls):
        stop_mailman(quiet=True, config=AppServerLayer.appserver_config)

    @classmethod
    def testSetUp(cls):
        pass

    @classmethod
    def testTearDown(cls):
        pass
