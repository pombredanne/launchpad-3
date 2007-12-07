# Copyright 2007 Canonical Ltd.  All rights reserved.
"""Browser code for the Launchpad root page."""

__metaclass__ = type
__all__ = [
    'LaunchpadRootIndexView',
    ]

from canonical.config import config
from canonical.launchpad.webapp import LaunchpadView
from canonical.launchpad.browser.announcement import HasAnnouncementsView


class LaunchpadRootIndexView(HasAnnouncementsView, LaunchpadView):
    """An view for the default view of the LaunchpadRoot."""

    def isRedirectInhibited(self):
        """Returns True if redirection has been inhibited."""
        return self.request.cookies.get('inhibit_beta_redirect', '0') == '1'

    def canRedirect(self):
        return bool(
            config.launchpad.beta_testers_redirection_host is not None and
            self.isBetaUser)


