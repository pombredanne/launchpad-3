# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Manage a Timeline for a request."""

__all__ = ['get_request_timeline']

__metaclass__ = type

from timeline import Timeline


def get_request_timeline(request):
    """Get a Timeline for request.

    This returns the request.annotations['timeline'], creating it if necessary.

    :param request: A zope/launchpad request object.
    :return: A lp.services.timeline.timeline.Timeline object for the request.
    """
    return request.annotations.setdefault('timeline', Timeline())
