# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).
"""Interfaces pertaining to the launchpad application.

Note that these are not interfaces to application content objects.
"""
__metaclass__ = type

from lazr.restful.interfaces import IServiceRootResource
from zope.interface import (
    Attribute,
    Interface,
    )
from zope.schema import (
    Bool,
    Int,
    )

from canonical.launchpad import _
from canonical.launchpad.webapp.interfaces import ILaunchpadApplication


__all__ = [
    'IAging',
    'IAuthServerApplication',
    'IHasAssignee',
    'IHasBug',
    'IHasDateCreated',
    'IHasIcon',
    'IHasLogo',
    'IHasMugshot',
    'IHasProduct',
    'IHasProductAndAssignee',
    'IPrivateApplication',
    'IPrivacy',
    'IWebServiceApplication',
    ]


class IPrivateApplication(ILaunchpadApplication):
    """Launchpad private XML-RPC application root."""

    authserver = Attribute("""Old Authserver API end point.""")

    codeimportscheduler = Attribute("""Code import scheduler end point.""")

    codehosting = Attribute("""Codehosting end point.""")

    mailinglists = Attribute("""Mailing list XML-RPC end point.""")

    bugs = Attribute("""Launchpad Bugs XML-RPC end point.""")

    softwarecenteragent = Attribute(
        """Software center agent XML-RPC end point.""")

    featureflags = Attribute("""Feature flag information endpoint""")


class IAuthServerApplication(ILaunchpadApplication):
    """Launchpad legacy AuthServer application root."""


class IWebServiceApplication(ILaunchpadApplication, IServiceRootResource):
    """Launchpad web service application root."""


class IHasAssignee(Interface):
    """An object that has an assignee."""

    assignee = Attribute("The object's assignee, which is an IPerson.")


class IHasProduct(Interface):
    """An object that has a product attribute that is an IProduct."""

    product = Attribute("The object's product")


class IHasBug(Interface):
    """An object linked to a bug, e.g., a bugtask or a bug branch."""

    bug = Int(title=_("Bug #"))


class IHasProductAndAssignee(IHasProduct, IHasAssignee):
    """An object that has a product attribute and an assigned attribute.
    See IHasProduct and IHasAssignee."""


class IHasIcon(Interface):
    """An object that can have a custom icon."""

    # Each of the objects that implements this needs a custom schema, so
    # here we can just use Attributes
    icon = Attribute("The 14x14 icon.")


class IHasLogo(Interface):
    """An object that can have a custom logo."""

    # Each of the objects that implements this needs a custom schema, so
    # here we can just use Attributes
    logo = Attribute("The 64x64 logo.")


class IHasMugshot(Interface):
    """An object that can have a custom mugshot."""

    # Each of the objects that implements this needs a custom schema, so
    # here we can just use Attributes
    mugshot = Attribute("The 192x192 mugshot.")


class IAging(Interface):
    """Something that gets older as time passes."""

    def currentApproximateAge():
        """Return a human-readable string of how old this thing is.

        Values returned are things like '2 minutes', '3 hours',
        '1 month', etc.
        """


class IPrivacy(Interface):
    """Something that can be private."""

    private = Bool(
        title=_("This is private"),
        required=False,
        description=_(
            "Private objects are visible to members or subscribers."))


class IHasDateCreated(Interface):
    """Something created on a certain date."""

    datecreated = Attribute("The date on which I was created.")
