# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Generic view class for comments."""

__metaclass__ = type
__all__ = [
    'CommentView'
    ]

from lazr.delegates import delegates

from canonical.launchpad.webapp import LaunchpadView
from lp.services.comments.interfaces.conversation import IComment


class CommentView(LaunchpadView):
    """The generic comment view just delegates to the context."""
    delegates(IComment)
