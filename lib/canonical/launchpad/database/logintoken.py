# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['LoginToken', 'LoginTokenSet']

import random

from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart

from zope.interface import implements
from zope.component import getUtility

from sqlobject import ForeignKey, StringCol, SQLObjectNotFound, AND

from canonical.config import config

from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol

from canonical.lp.dbschema import LoginTokenType

from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.helpers import get_email_template
from canonical.launchpad.mail import simple_sendmail, sendmail, format_address
from canonical.launchpad.interfaces import (
    ILoginToken, ILoginTokenSet, IGPGHandler, NotFoundError, IPersonSet)
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
    tokentype = EnumCol(dbName='tokentype', notNull=True,
                        schema=LoginTokenType)
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
        formatted_uids = ''
        for email in key.emails:
            formatted_uids += '\t%s\n' % email

        assert self.tokentype in (LoginTokenType.VALIDATEGPG,
                                  LoginTokenType.VALIDATESIGNONLYGPG)

        # Craft the confirmation that will be sent to the user.  There are two
        # parts, collected into a multipart/alternative.  Both sub-parts will
        # be text/plain, but the encrypted part, which must come second, will
        # have a charset of utf-8.  There's no perfect way to tell a mail
        # browser to display the clear text message only if it can't decode
        # the encrypted part, because with ASCII armor, both will be
        # text/plain.  This is the best we can do.

        # Start with the encrypted part, which must come first.
        template = get_email_template('validate-gpg.txt')
        replacements = {'requester': self.requester.browsername,
                        'requesteremail': self.requesteremail,
                        'displayname': key.displayname, 
                        'fingerprint': key.fingerprint,
                        'uids': formatted_uids,
                        'token_url': canonical_url(self)}

        body = template % replacements
        # Encrypt this part's content if requested
        if key.can_encrypt:
            gpghandler = getUtility(IGPGHandler)
            body = gpghandler.encryptContent(body.encode('utf-8'),
                                             key.fingerprint)
            encrypted_part = MIMEText(body, 'utf-8')
        else:
            # XXX: BarryWarsaw 23-Mar-2007 Should we even mail this
            # confirmation if the registered key is not an encrypting key?
            # Maybe we should send some other kind of confirmation message?
            encrypted_part = MIMEText(body)

        # And now the clear text part
        body = get_email_template('gpg-cleartext-instructions.txt')
        cleartext_part = MIMEText(body)

        # Put the parts together
        outer = MIMEMultipart('alternative',
                              _subparts=(cleartext_part, encrypted_part))
        outer['From'] = format_address("Launchpad OpenPGP Key Confirmation",
                                       config.noreply_from_address)
        outer['To'] = str(self.email)
        outer['Subject'] = "Launchpad: Confirm your OpenPGP Key"
        sendmail(outer)

    def sendPasswordResetEmail(self):
        """See ILoginToken."""
        template = get_email_template('forgottenpassword.txt')
        fromaddress = format_address("Launchpad", config.noreply_from_address)
        replacements = {'toaddress': self.email, 
                        'token_url': canonical_url(self)}
        message = template % replacements

        subject = "Launchpad: Forgotten Password"
        simple_sendmail(fromaddress, str(self.email), subject, message)

    def sendNewUserEmail(self):
        """See ILoginToken."""
        template = get_email_template('newuser-email.txt')
        replacements = {'token_url': canonical_url(self)}
        message = template % replacements

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
            # XXX: Aha! According to our policy, we shouldn't raise ValueError.
            # -- Guilherme Salgado, 2005-12-09
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
