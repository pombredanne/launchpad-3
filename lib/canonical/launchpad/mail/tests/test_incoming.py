# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import unittest

from zope.testing.doctest import DocTestSuite

from canonical.launchpad.mail.incoming import handleMail, MailErrorUtility
from canonical.testing import LaunchpadZopelessLayer
from lp.testing import TestCaseWithFactory
from lp.testing.mail_helpers import pop_notifications
from lp.services.mail.sendmail import MailController


class TestIncoming(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def test_invalid_signature(self):
        """Invalid signature should not be handled as an OOPs.

        It should produce a message explaining to the user what went wrong.
        """
        person = self.factory.makePerson()
        email_address = person.preferredemail.email
        invalid_body = (
            '-----BEGIN PGP SIGNED MESSAGE-----\n'
            'Hash: SHA1\n\n'
            'Body\n'
            '-----BEGIN PGP SIGNATURE-----\n'
            'Not a signature.\n'
            '-----END PGP SIGNATURE-----\n')
        ctrl = MailController(
            email_address, 'to@example.com', 'subject', invalid_body,
            bulk=False)
        ctrl.send()
        error_utility = MailErrorUtility()
        old_oops = error_utility.getLastOopsReport()
        handleMail()
        current_oops = error_utility.getLastOopsReport()
        if old_oops is None:
            self.assertIs(None, current_oops)
        else:
            self.assertEqual(old_oops.id, current_oops.id)
        (notification,) = pop_notifications()
        body = notification.get_payload()[0].get_payload(decode=True)
        self.assertIn(
            "An error occurred while processing a mail you sent to "
            "Launchpad's email\ninterface.\n\n\n"
            "Error message:\n\nSignature couldn't be verified: No data",
            body)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromName(__name__))
    suite.addTest(DocTestSuite('canonical.launchpad.mail.incoming'))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
