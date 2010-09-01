# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Manage a Timeline for a request."""

__all__ = ['get_request_timeline', 'set_request_timeline']

__metaclass__ = type

# XXX: undesirable but pragmatic. bug=623199 RBC 20100901
from canonical.launchpad import webapp
from timeline import Timeline


def get_request_timeline(request):
    """Get a Timeline for request.

    This returns the request.annotations['timeline'], creating it if necessary.

    :param request: A zope/launchpad request object.
    :return: A lp.services.timeline.timeline.Timeline object for the request.
    """
    try:
        return webapp.adapter._local.request_timeline
    except AttributeError:
        return set_request_timeline(request, Timeline())
    # Disabled code path: bug 623199
    return request.annotations.setdefault('timeline', Timeline())


def set_request_timeline(request, timeline):
    """Explicitly set a tiemline for request.

    This is used by code which wants to manually assemble a timeline.

    :param request: A zope/launchpad request object.
    :param timeline: A Timeline.
    """
    webapp.adapter._local.request_timeline = timeline
    return timeline
    # Disabled code path: bug 623199
    request.annotations['timeline'] = timeline
