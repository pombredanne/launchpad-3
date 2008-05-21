# Copyright 2004-2008 Canonical Ltd.  All rights reserved.
"""
Fixtures for running the Google test webservice.
"""

__metaclass__ = type

__all__ = ['GoogleServiceTestSetup']


import subprocess
import os
import signal


class GoogleServiceTestSetup:
    """Set up the Google web service stub for use in functional tests.

    >>> from canonical.launchpad.testing.googletestservice import (
    ...     service_is_available)
    >>> from canonical.config import config

    >>> assert not service_is_available()  # Sanity check.

    >>> GoogleServiceTestSetup().setUp()

    After setUp is called, a Google test service instance is running.

    >>> assert service_is_available()
    >>> assert GoogleServiceTestSetup.service is not None

    After tearDown is called, the service is shut down.

    >>> GoogleServiceTestSetup().tearDown()

    >>> assert not service_is_available()
    >>> assert GoogleServiceTestSetup.service is None

    The fixture can be started and stopped multiple time in succession:
    >>> GoogleServiceTestSetup().setUp()
    >>> assert service_is_available()

    Tidy up.

    >>> GoogleServiceTestSetup().tearDown()
    >>> assert not service_is_available()

    """

    service = None  # A reference to our running service.

    def setUp(self):
        self.startService()

    def tearDown(self):
        self.stopService()

    @classmethod
    def startService(cls):
        """Start the webservice."""
        assert not cls.service  # Sanity check.
        from canonical.launchpad.testing import googletestservice
        cls.service = googletestservice.start_as_process()
        assert cls.service, "The Search service process did not start."

    @classmethod
    def stopService(cls):
        """Shut down the webservice instance."""
        if cls.service:
            pid = cls.service.pid
            os.kill(pid, signal.SIGTERM)
            os.waitpid(pid, 0)
        cls.service = None
