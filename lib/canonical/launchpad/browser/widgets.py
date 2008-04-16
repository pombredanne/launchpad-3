# Copyright 2004-2008 Canonical Ltd.  All rights reserved.

"""Customized widgets used in Launchpad."""

__metaclass__ = type

__all__ = [
    'BranchPopupWidget',
    'DescriptionWidget',
    'ShipItAddressline1Widget',
    'ShipItAddressline2Widget',
    'ShipItCityWidget',
    'ShipItOrganizationWidget',
    'ShipItPhoneWidget',
    'ShipItProvinceWidget',
    'ShipItQuantityWidget',
    'ShipItReasonWidget',
    'ShipItRecipientDisplaynameWidget',
    'SummaryWidget',
    'TitleWidget',
    'WhiteboardWidget',
    ]


from zope.app.form.browser import TextAreaWidget, TextWidget, IntWidget
from zope.component import getUtility

from canonical.launchpad.interfaces import BranchType, IBranchSet
from canonical.launchpad.webapp.interfaces import ILaunchBag
from canonical.launchpad.webapp.uri import URI
from canonical.widgets import SinglePopupWidget, StrippedTextWidget


class TitleWidget(StrippedTextWidget):
    """A launchpad title widget; a little wider than a normal Textline."""
    displayWidth = 44


class SummaryWidget(TextAreaWidget):
    """A widget to capture a summary."""
    width = 44
    height = 3


class DescriptionWidget(TextAreaWidget):
    """A widget to capture a description."""
    width = 44
    height = 5


class WhiteboardWidget(TextAreaWidget):
    """A widget to capture a whiteboard."""
    width = 44
    height = 5


class ShipItRecipientDisplaynameWidget(TextWidget):
    """See IShipItRecipientDisplayname"""
    displayWidth = displayMaxWidth = 20


class ShipItOrganizationWidget(TextWidget):
    """See IShipItOrganization"""
    displayWidth = displayMaxWidth = 30


class ShipItCityWidget(TextWidget):
    """See IShipItCity"""
    displayWidth = displayMaxWidth = 30


class ShipItProvinceWidget(TextWidget):
    """See IShipItProvince"""
    displayWidth = displayMaxWidth = 30


class ShipItAddressline1Widget(TextWidget):
    """See IShipItAddressline1"""
    displayWidth = displayMaxWidth = 30


class ShipItAddressline2Widget(TextWidget):
    """See IShipItAddressline2"""
    displayWidth = displayMaxWidth = 30


class ShipItPhoneWidget(TextWidget):
    """See IShipItPhone"""
    displayWidth = displayMaxWidth = 16


class ShipItReasonWidget(TextAreaWidget):
    """See IShipItReason"""
    width = 40
    height = 4


class ShipItQuantityWidget(IntWidget):
    """See IShipItQuantity"""
    displayWidth = 4
    displayMaxWidth = 3
    style = 'text-align: right'


class BranchPopupWidget(SinglePopupWidget):
    """Custom popup widget for choosing branches."""

    displayWidth = '35'

    def _isBranchWithName(self, name):
        product = self.getProduct()
        results = getUtility(IBranchSet).getByProductAndName(product, name)
        return results.count() > 0

    def getBranchNameFromURL(self, url, MAXIMUM_TRIES=10):
        """Return a branch name based on `url`.

        The name is based on the last path segment of the URL. If there is
        already another branch of that name on the product, then we'll try to
        find a unique name by appending numbers. Do this up to `MAXIMUM_TRIES`
        times.
        """
        original_name = name = URI(url).path.split('/')[-1]
        for i in range(1, MAXIMUM_TRIES+1):
            if not self._isBranchWithName(name):
                return name
            name = '%s-%d' % (original_name, i)

    def getPerson(self):
        """Return the person in the context, if any."""
        return getUtility(ILaunchBag).user

    def getProduct(self):
        """Return the product in the context, if there is one."""
        return getUtility(ILaunchBag).product

    def makeBranchFromURL(self, url):
        owner = self.getPerson()
        return getUtility(IBranchSet).new(
            BranchType.MIRRORED, 'foo', owner, owner, self.getProduct(), url)
