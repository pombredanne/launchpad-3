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

    def _getUsedNumbers(self, branch_set, product, name):
        """Iterate over numbers that have previously been appended to name.

        Finds all of the branches in `product` that have name like 'name-%'.
        It iterates over all of those, yielding numbers that occur after the
        final dash of such names.

        This lets us easily pick a number that *hasn't* been used.
        """
        similar_branches = branch_set.getByProductAndNameStartsWith(
            product, name + '-')
        # 0 is always used, so that if there are no names like 'name-N', we
        # will start with name-1.
        yield 0
        for branch in similar_branches:
            last_token = branch.name.split('-')[-1]
            try:
                yield int(last_token)
            except ValueError:
                # It's not an integer, so we don't care.
                pass

    def getBranchNameFromURL(self, url):
        """Return a branch name based on `url`.

        The name is based on the last path segment of the URL. If there is
        already another branch of that name on the product, then we'll try to
        find a unique name by appending numbers.
        """
        name = URI(url).path.split('/')[-1]
        product = self.getProduct()
        branch_set = getUtility(IBranchSet)
        if branch_set.getByProductAndName(product, name).count() == 0:
            return name

        # Get a unique name that's `name` plus a number.
        next_number = max(self._getUsedNumbers(branch_set, product, name)) + 1
        name = '%s-%s' % (name, next_number)
        return name

    def getPerson(self):
        """Return the person in the context, if any."""
        return getUtility(ILaunchBag).user

    def getProduct(self):
        """Return the product in the context, if there is one."""
        return getUtility(ILaunchBag).product

    def makeBranchFromURL(self, url):
        owner = self.getPerson()
        name = self.getBranchNameFromURL(url)
        return getUtility(IBranchSet).new(
            BranchType.MIRRORED, name, owner, owner, self.getProduct(), url)
