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
from zope.schema import (
    Bool,
    Choice,
    )

from canonical.launchpad import _
from lp.app.enums import ServiceUsage


class IServiceUsage(Interface):
    """Pillar service usages."""

    # XXX: BradCrittenden 2010-08-06 bug=n/a:  I hate using the term 'pillar'
    # but cannot use 'project' or 'distribution'.  The phrase 'Where does'
    # implies an actual location not an answer of "Launchpad, externally, or
    # neither."
    answers_usage = Choice(
        title=_('Type of service for answers application'),
        description=_("Where does this pillar have an Answers forum?"),
        default=ServiceUsage.UNKNOWN,
        vocabulary=ServiceUsage)
    blueprints_usage = Choice(
        title=_('Type of service for blueprints application'),
        description=_("Where does this pillar host blueprints?"),
        default=ServiceUsage.UNKNOWN,
        vocabulary=ServiceUsage)
    codehosting_usage = Choice(
        title=_('Type of service for hosting code'),
        description=_("Where does this pillar host code?"),
        default=ServiceUsage.UNKNOWN,
        vocabulary=ServiceUsage)
    translations_usage = Choice(
        title=_('Type of service for translations application'),
        description=_("Where does this pillar do translations?"),
        default=ServiceUsage.UNKNOWN,
        vocabulary=ServiceUsage)
    bug_tracking_usage = Choice(
        title=_('Type of service for tracking bugs'),
        description=_("Where does this pillar track bugs?"),
        default=ServiceUsage.UNKNOWN,
        vocabulary=ServiceUsage)
    uses_launchpad = Bool(
        title=_('Uses Launchpad for something.'))


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
        title=_('Uses Launchpad for something'))
    enable_bug_expiration = Bool(
        title=_('Expire "Incomplete" bug reports when they become inactive'),
        required=True)
