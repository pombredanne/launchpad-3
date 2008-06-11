# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces related to Salesforce vouchers."""

__metaclass__ = type

__all__ = [
    'ISalesforceVoucher',
    'ISalesforceVoucherProxy',
    ]

from zope.interface import Interface
from zope.schema import Choice, Int, TextLine

from canonical.launchpad import _


class ISalesforceVoucherProxy(Interface):
    """Wrapper class for voucher processing with Salesforce.

    These vouchers are used to allow commercial projects to subscribe to
    Launchpad.
    """

    def getUnredeemedVouchers(user):
        """Get the unredeemed vouchers for the user."""

    def getAllVouchers(user):
        """Get all of the vouchers for the user."""

    def getServerStatus():
        """Get the server status."""

    def getVoucher(voucher_id):
        """Lookup a voucher."""

    def redeemVoucher(voucher_id, user, project):
        """Redeem a voucher.

        :param voucher_id: string with the id of the voucher to be redeemed.
        :param user: user who is redeeming the voucher.
        :param project: project that is being subscribed.
        :return: list with a boolean indicating status of redemption, and an
            integer representing the number of months the subscription
            allows.
        """

    def updateProjectName(project):
        """Update the name of a project in Salesforce.

        If a project changes its name it is updated in Salesforce.
        :param project: the project to update
        :return: integer representing the number of vouchers found for this
            project which were updated.
        """

class ISalesforceVoucher(Interface):
    """Vouchers in Salesforce."""

    voucher_id = TextLine(
        title=_("Voucher ID"),
        description=_("The id for the voucher."))
    project = Choice(
        title=_('Project'),
        required=False,
        vocabulary='Product',
        description=_("The project the voucher is redeemed against."))
    status = TextLine(
        title=_("Status"),
        description=_("The voucher's redemption status."))
    term_months = Int(
        title=_("Term in months"),
        description=_("The voucher can be redeemed for a subscription "
                      "for this number of months."))
