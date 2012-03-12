# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'product_licenses_modified',
    ]

from datetime import datetime

import pytz

from zope.security.proxy import removeSecurityProxy

from lp.registry.interfaces.person import IPerson
from lp.registry.interfaces.product import License
from lp.services.config import config
from lp.services.mail.helpers import get_email_template
from lp.services.mail.sendmail import (
    format_address,
    simple_sendmail,
    )
from lp.services.webapp.publisher import canonical_url


def product_licenses_modified(product, event):
    if 'licenses' not in event.edited_fields:
        return
    licenses = list(product.licenses)
    needs_email = (
        License.OTHER_PROPRIETARY in licenses
        or License.OTHER_OPEN_SOURCE in licenses
        or [License.DONT_KNOW] == licenses)
    if not needs_email:
        # The project has a recognized license.
        return
    user = IPerson(event.user)
    notification = LicenseNotification(product, user)
    notification.send()


class LicenseNotification:
    # XXX sinzui 2012-03-09: This was extracted from ProductLicenseMixin in
    # lp.registry.browser.product.

    def __init__(self, product, user):
        self.product = product
        self.user = user

    def send(self):
        licenses = list(self.product.licenses)
        needs_email = (
            License.OTHER_PROPRIETARY in licenses
            or License.OTHER_OPEN_SOURCE in licenses
            or [License.DONT_KNOW] == licenses)
        if not needs_email:
            # The project has a recognized license.
            return False
        user_address = format_address(
            self.user.displayname, self.user.preferredemail.email)
        from_address = format_address(
            "Launchpad", config.canonical.noreply_from_address)
        commercial_address = format_address(
            'Commercial', 'commercial@launchpad.net')
        license_titles = '\n'.join(
            license.title for license in self.product.licenses)
        substitutions = dict(
            user_browsername=self.user.displayname,
            user_name=self.user.name,
            product_name=self.product.name,
            product_url=canonical_url(self.product),
            product_summary=self._indent(self.product.summary),
            license_titles=self._indent(license_titles),
            license_info=self._indent(self.product.license_info))
        # Email the user about license policy.
        subject = (
            "License information for %(product_name)s "
            "in Launchpad" % substitutions)
        template = get_email_template(
            'product-other-license.txt', app='registry')
        message = template % substitutions
        simple_sendmail(
            from_address, user_address,
            subject, message, headers={'Reply-To': commercial_address})
        # Inform that Launchpad recognized the license change.
        self._addLicenseChangeToReviewWhiteboard()
        return True

    @staticmethod
    def _indent(text):
        if text is None:
            return None
        text = '\n    '.join(line for line in text.split('\n'))
        text = '    ' + text
        return text

    def _addLicenseChangeToReviewWhiteboard(self):
        """Update the whiteboard for the reviewer's benefit."""
        now = self._formatDate()
        whiteboard = 'User notified of license policy on %s.' % now
        naked_product = removeSecurityProxy(self.product)
        if naked_product.reviewer_whiteboard is None:
            naked_product.reviewer_whiteboard = whiteboard
        else:
            naked_product.reviewer_whiteboard += '\n' + whiteboard

    @staticmethod
    def _formatDate(now=None):
        """Return the date formatted for messages."""
        if now is None:
            now = datetime.now(tz=pytz.UTC)
        return now.strftime('%Y-%m-%d')
