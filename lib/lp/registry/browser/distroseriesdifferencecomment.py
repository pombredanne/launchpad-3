# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""View and helper for `DistroSeriesDifferenceComment`."""

__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.webapp import LaunchpadView
from lp.app.interfaces.launchpad import ILaunchpadCelebrities


class DistroSeriesDifferenceCommentView(LaunchpadView):
    """View class for `DistroSeriesDifferenceComment`.

    :ivar css_class: The CSS class for this comment.  Package copy failures
        are stored as `DistroSeriesDifferenceComments`, but rendered to be
        visually recognizable as errors.
    """

    def __init__(self, *args, **kwargs):
        super(DistroSeriesDifferenceCommentView, self).__init__(
            *args, **kwargs)
        error_persona = getUtility(ILaunchpadCelebrities).janitor
        if self.context.comment_author == error_persona:
            self.css_class = "sprite error-icon"
        else:
            self.css_class = ""
