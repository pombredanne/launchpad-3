# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""A Twisted job to touch the GPGHandler config files."""

__metaclass__ = type
__all__ = [
    'GPGHandlerConfigResetJob',
    ]

from twisted.application.service import Service
from twisted.internet import task
from twisted.internet.error import AlreadyCancelled

from zope.component import getUtility
from zope.component.interfaces import ComponentLookupError

from canonical.launchpad.interfaces.gpghandler import IGPGHandler


class GPGHandlerConfigResetJob(Service):
    """Manages twisted job to touch the files in the gpgconfig directory."""

    def startService(self):
        self._gpghandler_job = None
        # start the GPGHandler job
        self._scheduleGPGHandlerJob()
        Service.startService(self)

    def stopService(self):
        self._stopGPGHandlerJob()
        Service.stopService(self)

    def _scheduleGPGHandlerJob(self, touch_interval=12 * 3600):
        # Create a job to touch the GPGHandler home directory every so often
        # so that it does not get cleaned up by any reaper scripts which look
        # at time last modified.

        self._stopGPGHandlerJob()
        self._gpghandler_job = task.LoopingCall(
            getUtility(IGPGHandler).touchConfigurationDirectory)
        return self._gpghandler_job.start(touch_interval)

    def _stopGPGHandlerJob(self):
        try:
            if self._gpghandler_job and self._gpghandler_job.running:
                self._gpghandler_job.stop()
        except AlreadyCancelled:
            # So we're already cancelled, meh.
            pass
