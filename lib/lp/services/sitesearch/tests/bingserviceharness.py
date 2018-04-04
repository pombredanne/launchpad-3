# Copyright 2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
Fixtures for running the Bing test webservice.
"""

__metaclass__ = type

__all__ = ['BingServiceTestSetup']


import errno
import os
import signal

from lp.services.sitesearch import bingtestservice


class BingServiceTestSetup:
    """Set up the Bing web service stub for use in functional tests.
    """

    # XXX gary 2008-12-06 bug=305858: Spurious test failures discovered on
    # buildbot, builds 40 and 43. The locations of the failures are marked
    # below with " # SPURIOUS FAILURE". To reinstate, add the text below back
    # to the docstring above.  Note that the test that uses this setup,
    # bing-service-stub.txt, is also disabled.  See test_doc.py.
    """
    >>> from lp.services.sitesearch.bingtestservice import (
    ...     service_is_available)
    >>> from lp.services.config import config

    >>> assert not service_is_available()  # Sanity check. # SPURIOUS FAILURE

    >>> BingServiceTestSetup().setUp()

    After setUp is called, a Bing test service instance is running.

    >>> assert service_is_available()
    >>> assert BingServiceTestSetup.service is not None

    After tearDown is called, the service is shut down.

    >>> BingServiceTestSetup().tearDown()

    >>> assert not service_is_available()
    >>> assert BingServiceTestSetup.service is None

    The fixture can be started and stopped multiple time in succession:

    >>> BingServiceTestSetup().setUp()
    >>> assert service_is_available()

    Having a service instance already running doesn't prevent a new
    service from starting.  The old instance is killed off and replaced
    by the new one.

    >>> old_pid = BingServiceTestSetup.service.pid
    >>> BingServiceTestSetup().setUp() # SPURIOUS FAILURE
    >>> BingServiceTestSetup.service.pid != old_pid
    True

    Tidy up.

    >>> BingServiceTestSetup().tearDown()
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
        bingtestservice.kill_running_process()
        cls.service = bingtestservice.start_as_process()
        assert cls.service, "The Search service process did not start."
        try:
            bingtestservice.wait_for_service()
        except RuntimeError:
            # The service didn't start itself soon enough.  We must
            # make sure to kill any errant processes that may be
            # hanging around.
            cls.stopService()
            raise

    @classmethod
    def stopService(cls):
        """Shut down the webservice instance."""
        if cls.service:
            try:
                os.kill(cls.service.pid, signal.SIGTERM)
            except OSError as error:
                if error.errno != errno.ESRCH:
                    raise
                # The process with the given pid doesn't exist, so there's
                # nothing to kill or wait for.
            else:
                cls.service.wait()
        cls.service = None
