# Copyright 2009 Canonical Ltd.  All rights reserved.

"""ZCML directive for help folder registrations."""

__metaclass__ = type
__all__ = []

import inspect

from zope.component.zcml import handler
from zope.configuration.fields import GlobalInterface, Path
from zope.publisher.interfaces.browser import (
    IBrowserRequest, IBrowserPublisher)
from zope.security.checker import defineChecker, NamesChecker

from zope.interface import Interface

from canonical.launchpad.webapp.interfaces import ILaunchpadApplication

from lp.services.inlinehelp.browser import HelpFolder


class IHelpFolderDirective(Interface):
    """Directive to register an help folder."""
    folder = Path(
        title=u'The path to the help folder.',
        required=True)
    type = GlobalInterface(
        title=u'The request type on which the help folder is registered',
        required=False,
        default=IBrowserRequest)


def register_help_folder(context, folder, type=IBrowserRequest):
    """Create a help folder subclass and register it with the ZCA."""

    # The type parameter shadows the builtin, so access it directly.
    help_folder = __builtins__['type'](
        str('+help for %s' % folder), (HelpFolder, ), {'folder': folder})

    defineChecker(
        help_folder,
        NamesChecker(list(IBrowserPublisher.names(True)) + ['__call__']))

    context.action(
        discriminator = ('view', (ILaunchpadApplication, type), '+help'),
        callable = handler,
        args = ('registerAdapter',
                help_folder, (ILaunchpadApplication, type), Interface,
                '+help', context.info),
        )
