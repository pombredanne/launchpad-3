# Copyright 2017-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Validators for the .store_channels attribute."""

__metaclass__ = type

from zope.schema.vocabulary import getVocabularyRegistry

from lp import _
from lp.app.validators import LaunchpadValidationError
from lp.services.webapp.escaping import (
    html_escape,
    structured,
    )


# delimiter separating channel components
channel_components_delimiter = '/'


def _is_risk(component):
    """Does this channel component identify a risk?"""
    vocabulary = getVocabularyRegistry().get(None, "SnapStoreChannel")
    try:
        vocabulary.getTermByToken(component)
    except LookupError:
        return False
    else:
        return True


def split_channel_name(channel):
    """Return extracted track, risk, and branch from given channel name."""
    components = channel.split(channel_components_delimiter)
    if len(components) == 3:
        track, risk, branch = components
    elif len(components) == 2:
        # Identify risk to determine if this is track/risk or risk/branch.
        if _is_risk(components[0]):
            if _is_risk(components[1]):
                raise ValueError(
                    "Branch name cannot match a risk name: %r" % channel)
            track = None
            risk, branch = components
        elif _is_risk(components[1]):
            track, risk = components
            branch = None
        else:
            raise ValueError("No valid risk provided: %r" % channel)
    elif len(components) == 1:
        track = None
        risk = components[0]
        branch = None
    else:
        raise ValueError("Invalid channel name: %r" % channel)
    return track, risk, branch


def channels_validator(channels):
    """Return True if the channels in a list are valid, or raise a
    LaunchpadValidationError.
    """
    tracks = set()
    branches = set()
    for name in channels:
        try:
            track, risk, branch = split_channel_name(name)
        except ValueError:
            message = _(
                "Invalid channel name '${name}'. Channel names must be of the "
                "form 'track/risk/branch', 'track/risk', 'risk/branch', or "
                "'risk'.",
                mapping={'name': html_escape(name)})
            raise LaunchpadValidationError(structured(message))
        tracks.add(track)
        branches.add(branch)

    # XXX cjwatson 2018-05-08: These are slightly arbitrary restrictions,
    # but they make the UI much simpler.

    if len(tracks) != 1:
        message = _("Channels must belong to the same track.")
        raise LaunchpadValidationError(structured(message))

    if len(branches) != 1:
        message = _("Channels must belong to the same branch.")
        raise LaunchpadValidationError(structured(message))

    return True
