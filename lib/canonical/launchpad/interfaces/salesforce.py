# Copyright 2004-2007 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

from zope.interface import Interface

__all__ = ['ISalesforceVoucherProxy']


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
