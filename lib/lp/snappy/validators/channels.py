# Copyright 2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Validators for the .store_channels attribute."""

__metaclass__ = type

from lp import _
from lp.app.validators import LaunchpadValidationError
from lp.services.webapp.escaping import (
    html_escape,
    structured,
    )


# delimiter separating channel components
channel_components_delimiter = '/'


def split_channel_name(channel):
    """Return extracted track and risk from given channel name."""
    components = channel.split(channel_components_delimiter)
    if len(components) == 2:
        track, risk = components
    elif len(components) == 1:
        track = None
        risk = components[0]
    else:
        raise ValueError("Invalid channel name: %r" % channel)
    return track, risk


def channels_validator(channels):
    """Return True if the channels in a list are valid, or raise a
    LaunchpadValidationError.
    """
    tracks = set()
    for name in channels:
        try:
            track, risk = split_channel_name(name)
        except ValueError:
            message = _(
                "Invalid channel name '${name}'. Channel names must be of the "
                "form 'track/risk' or 'risk'.",
                mapping={'name': html_escape(name)})
            raise LaunchpadValidationError(structured(message))
        tracks.add(track)

    if len(tracks) != 1:
        message = _("Channels must belong to the same track.")
        raise LaunchpadValidationError(structured(message))

    return True
