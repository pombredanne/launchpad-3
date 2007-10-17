# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['LoginToken', 'LoginTokenSet']

import random

from zope.interface import implements
from zope.component import getUtility

from sqlobject import ForeignKey, StringCol, SQLObjectNotFound, AND

from canonical.config import config

from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol

from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.helpers import get_email_template
from canonical.launchpad.mail import simple_sendmail, format_address
from canonical.launchpad.interfaces import (
    ILoginToken, ILoginTokenSet, IGPGHandler, NotFoundError, IPersonSet,
    LoginTokenType)
from canonical.launchpad.validators.email import valid_email


class LoginToken(SQLBase):
    implements(ILoginToken)
    _table = 'LoginToken'

    redirection_url = StringCol(default=None)
    requester = ForeignKey(dbName='requester', foreignKey='Person')
    requesteremail = StringCol(dbName='requesteremail', notNull=False,
                               default=None)
    email = StringCol(dbName='email', notNull=True)
    token = StringCol(dbName='token', unique=True)
    tokentype = EnumCol(dbName='tokentype', notNull=True, enum=LoginTokenType)
    created = UtcDateTimeCol(dbName='created', notNull=True)
    fingerprint = StringCol(dbName='fingerprint', notNull=False,
                            default=None)
    date_consumed = UtcDateTimeCol(default=None)
    password = '' # Quick fix for Bug #2481

    title = 'Launchpad Email Verification'

    def consume(self):
        """See ILoginToken."""
        self.date_consumed = UTC_NOW

        if self.fingerprint is not None:
            tokens = LoginTokenSet().searchByFingerprintRequesterAndType(
                self.fingerprint, self.requester, self.tokentype)
        else:
            tokens = LoginTokenSet().searchByEmailRequesterAndType(
                self.email, self.requester, self.tokentype)

        for token in tokens:
            token.date_consumed = UTC_NOW

    def sendEmailValidationRequest(self, appurl):
        """See ILoginToken."""
        template = get_email_template('validate-email.txt')
        fromaddress = format_address(
            "Launchpad Email Validator", config.noreply_from_address)

        replacements = {'longstring': self.token,
                        'requester': self.requester.browsername,
                        'requesteremail': self.requesteremail,
                        'toaddress': self.email,
                        'appurl': appurl}
        message = template % replacements

        subject = "Launchpad: Validate your email address"
        simple_sendmail(fromaddress, str(self.email), subject, message)

    def sendGPGValidationRequest(self, key):
        """See ILoginToken."""
        separator = '\n    '
        formatted_uids = '    ' + separator.join(key.emails)

        assert self.tokentype in (LoginTokenType.VALIDATEGPG,
                                  LoginTokenType.VALIDATESIGNONLYGPG)

        # Craft the confirmation message that will be sent to the user.  There
        # are two chunks of text that will be concatenated together into a
        # single text/plain part.  The first chunk will be the clear text
        # instructions providing some extra help for those people who cannot
        # read the encrypted chunk that follows.  The encrypted chunk will
        # have the actual confirmation token in it, however the ability to
        # read this is highly dependent on the mail reader being used, and how
        # that MUA is configured.

        # Here are the instructions that need to be encrypted.
        template = get_email_template('validate-gpg.txt')
        replacements = {'requester': self.requester.browsername,
                        'requesteremail': self.requesteremail,
                        'displayname': key.displayname,
                        'fingerprint': key.fingerprint,
                        'uids': formatted_uids,
                        'token_url': canonical_url(self)}

        token_text = template % replacements
        salutation = 'Hello,\n\n'
        instructions = ''
        closing = """
Thanks,

The Launchpad Team"""

        # Encrypt this part's content if requested.
        if key.can_encrypt:
            gpghandler = getUtility(IGPGHandler)
            token_text = gpghandler.encryptContent(token_text.encode('utf-8'),
                                                   key.fingerprint)
            # In this case, we need to include some clear text instructions
            # for people who do not have an MUA that can decrypt the ASCII
            # armored text.
            instructions = get_email_template('gpg-cleartext-instructions.txt')

        # Concatenate the message parts and send it.
        text = salutation + instructions + token_text + closing
        simple_sendmail(format_address('Launchpad OpenPGP Key Confirmation',
                                       config.noreply_from_address),
                        str(self.email),
                        'Launchpad: Confirm your OpenPGP Key',
                        text)

    def sendPasswordResetNeutralEmail(self):
        """See ILoginToken."""
        template = get_email_template('forgottenpassword-neutral.txt')
        fromaddress = format_address(
            "Login Service", config.noreply_from_address)
        message = template % dict(token_url=canonical_url(self))
        subject = "Login Service: Forgotten Password"
        simple_sendmail(fromaddress, str(self.email), subject, message)

    def sendNewUserNeutralEmail(self):
        """See ILoginToken."""
        template = get_email_template('newuser-email-neutral.txt')
        message = template % dict(token_url=canonical_url(self))

        fromaddress = format_address("Launchpad", config.noreply_from_address)
        subject = "Login Service: Finish your registration"
        simple_sendmail(fromaddress, str(self.email), subject, message)

    def sendPasswordResetEmail(self):
        """See ILoginToken."""
        template = get_email_template('forgottenpassword.txt')
        fromaddress = format_address(
            "Login Service", config.noreply_from_address)
        message = template % dict(token_url=canonical_url(self))
        subject = "Login Service: Forgotten Password"
        simple_sendmail(fromaddress, str(self.email), subject, message)

    def sendNewUserEmail(self):
        """See ILoginToken."""
        template = get_email_template('newuser-email.txt')
        message = template % dict(token_url=canonical_url(self))

        fromaddress = format_address("Launchpad", config.noreply_from_address)
        subject = "Finish your Launchpad registration"
        simple_sendmail(fromaddress, str(self.email), subject, message)

    def sendProfileCreatedEmail(self, profile, comment):
        """See ILoginToken."""
        template = get_email_template('profile-created.txt')
        replacements = {'token_url': canonical_url(self),
                        'requester': self.requester.browsername,
                        'comment': comment,
                        'profile_url': canonical_url(profile)}
        message = template % replacements

        headers = {'Reply-To': self.requester.preferredemail.email}
        fromaddress = format_address("Launchpad", config.noreply_from_address)
        subject = "Launchpad profile"
        simple_sendmail(
            fromaddress, str(self.email), subject, message, headers=headers)

    def sendMergeRequestEmail(self):
        """See ILoginToken."""
        template = get_email_template('request-merge.txt')
        fromaddress = format_address(
            "Launchpad Account Merge", config.noreply_from_address)

        dupe = getUtility(IPersonSet).getByEmail(self.email)
        replacements = {'dupename': "%s (%s)" % (dupe.browsername, dupe.name),
                        'requester': self.requester.name,
                        'requesteremail': self.requesteremail,
                        'toaddress': self.email,
                        'token_url': canonical_url(self)}
        message = template % replacements

        subject = "Launchpad: Merge of Accounts Requested"
        simple_sendmail(fromaddress, str(self.email), subject, message)

    def sendTeamEmailAddressValidationEmail(self, user):
        """See ILoginToken."""
        template = get_email_template('validate-teamemail.txt')

        fromaddress = format_address(
            "Launchpad Email Validator", config.noreply_from_address)
        subject = "Launchpad: Validate your team's contact email address"
        replacements = {'team': self.requester.browsername,
                        'requester': '%s (%s)' % (user.browsername, user.name),
                        'toaddress': self.email,
                        'admin_email': config.admin_address,
                        'token_url': canonical_url(self)}
        message = template % replacements
        simple_sendmail(fromaddress, str(self.email), subject, message)

    def sendClaimProfileEmail(self):
        """See ILoginToken."""
        template = get_email_template('claim-profile.txt')
        fromaddress = format_address("Launchpad", config.noreply_from_address)
        profile = getUtility(IPersonSet).getByEmail(self.email)
        replacements = {'profile_name': (
                            "%s (%s)" % (profile.browsername, profile.name)),
                        'email': self.email,
                        'token_url': canonical_url(self)}
        message = template % replacements

        subject = "Launchpad: Claim Profile"
        simple_sendmail(fromaddress, str(self.email), subject, message)


class LoginTokenSet:
    implements(ILoginTokenSet)

    def __init__(self):
        self.title = 'Launchpad e-mail address confirmation'

    def get(self, id, default=None):
        """See ILoginTokenSet."""
        try:
            return LoginToken.get(id)
        except SQLObjectNotFound:
            return default

    def searchByEmailRequesterAndType(self, email, requester, type):
        """See ILoginTokenSet."""
        requester_id = None
        if requester is not None:
            requester_id = requester.id
        return LoginToken.select(AND(LoginToken.q.email==email,
                                     LoginToken.q.requesterID==requester_id,
                                     LoginToken.q.tokentype==type))

    def deleteByEmailRequesterAndType(self, email, requester, type):
        """See ILoginTokenSet."""
        for token in self.searchByEmailRequesterAndType(email, requester, type):
            token.destroySelf()

    def searchByFingerprintRequesterAndType(self, fingerprint, requester, type):
        """See ILoginTokenSet."""
        return LoginToken.select(AND(LoginToken.q.fingerprint==fingerprint,
                                     LoginToken.q.requesterID==requester.id,
                                     LoginToken.q.tokentype==type))

    def getPendingGPGKeys(self, requesterid=None):
        """See ILoginTokenSet."""
        query = ('date_consumed IS NULL AND '
                 '(tokentype = %s OR tokentype = %s) '
                 % sqlvalues(LoginTokenType.VALIDATEGPG,
                 LoginTokenType.VALIDATESIGNONLYGPG))

        if requesterid:
            query += 'AND requester=%s' % requesterid

        return LoginToken.select(query)

    def deleteByFingerprintRequesterAndType(self, fingerprint, requester, type):
        tokens = self.searchByFingerprintRequesterAndType(
            fingerprint, requester, type)
        for token in tokens:
            token.destroySelf()

    def new(self, requester, requesteremail, email, tokentype,
            fingerprint=None, redirection_url=None):
        """See ILoginTokenSet."""
        assert valid_email(email)
        if tokentype not in LoginTokenType.items:
            # XXX: Guilherme Salgado, 2005-12-09:
            # Aha! According to our policy, we shouldn't raise ValueError.
            raise ValueError(
                "tokentype is not an item of LoginTokenType: %s" % tokentype)

        characters = '0123456789bcdfghjklmnpqrstvwxzBCDFGHJKLMNPQRSTVWXZ'
        length = 20
        token = ''.join([random.choice(characters) for count in range(length)])
        reqid = getattr(requester, 'id', None)
        return LoginToken(requesterID=reqid, requesteremail=requesteremail,
                          email=email, token=token, tokentype=tokentype,
                          created=UTC_NOW, fingerprint=fingerprint,
                          redirection_url=redirection_url)

    def __getitem__(self, tokentext):
        """See ILoginTokenSet."""
        token = LoginToken.selectOneBy(token=tokentext)
        if token is None:
            raise NotFoundError(tokentext)
        return token
