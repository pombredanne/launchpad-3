# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Interfaces for the Launchpad application.

Note that these are not interfaces to application content objects.
"""

__metaclass__ = type

__all__ = [
    'ILaunchpadUsage',
    'IServiceUsage',
    ]

from zope.interface import Interface
from zope.schema import Bool, Choice

from canonical.launchpad import _
from lp.app.enums import LaunchpadServiceUsage


class IServiceUsage(Interface):
    """Project service usages."""

    answers_usage = Choice(
        title=_('Location of answers'),
        required=True,
        readonly=True,
        description=_("Where does this project host an answers forum?"),
        default=LaunchpadServiceUsage.UNKNOWN,
        vocabulary=LaunchpadServiceUsage)
    blueprints_usage = Choice(
        title=_('Location of blueprints'),
        required=True,
        readonly=True,
        description=_("Where does this project host blueprints?"),
        default=LaunchpadServiceUsage.UNKNOWN,
        vocabulary=LaunchpadServiceUsage)
    codehosting_usage = Choice(
        title=_('Location of code hosting'),
        required=True,
        readonly=True,
        description=_("Where does this project host code?"),
        default=LaunchpadServiceUsage.UNKNOWN,
        vocabulary=LaunchpadServiceUsage)
    translations_usage = Choice(
        title=_('Location of translations'),
        required=True,
        readonly=True,
        description=_("Where does this project do translations?"),
        default=LaunchpadServiceUsage.UNKNOWN,
        vocabulary=LaunchpadServiceUsage)
    bug_tracking_usage = Choice(
        title=_('Location of bug tracking'),
        required=True,
        readonly=True,
        description=_("Where does this project track bugs?"),
        default=LaunchpadServiceUsage.UNKNOWN,
        vocabulary=LaunchpadServiceUsage)
    uses_launchpad = Bool(
        title=_('Uses Launchpad for something'))


class ILaunchpadUsage(Interface):
    """How the project uses Launchpad."""
    official_answers = Bool(
        title=_('People can ask questions in Launchpad Answers'),
        required=True)
    official_blueprints = Bool(
        title=_('This project uses blueprints'), required=True)
    official_codehosting = Bool(
        title=_('Code for this project is published in Bazaar branches on'
                ' Launchpad'),
        required=True)
    official_malone = Bool(
        title=_('Bugs in this project are tracked in Launchpad'),
        required=True)
    official_rosetta = Bool(
        title=_('Translations for this project are done in Launchpad'),
        required=True)
    official_anything = Bool(
        title=_('Uses Launchpad for something'),)
    enable_bug_expiration = Bool(
        title=_('Expire "Incomplete" bug reports when they become inactive'),
        required=True)
