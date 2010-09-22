# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""ZCML directive for help folder registrations."""

__metaclass__ = type
__all__ = []

from zope.component.zcml import handler
from zope.configuration.fields import (
    GlobalInterface,
    Path,
    )
from zope.interface import Interface
from zope.publisher.interfaces.browser import (
    IBrowserPublisher,
    IBrowserRequest,
    )
from zope.security.checker import (
    defineChecker,
    NamesChecker,
    )

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

    # ZCML pass the type parameter via keyword parameters, so it can't be
    # renamed and shadows the builtin. So access that type() builtin directly.
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
