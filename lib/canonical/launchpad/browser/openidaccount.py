# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Browser code related to Accounts on the OpenID server."""

__metaclass__ = type
__all__ = []

import urllib

from zope.component import getUtility
from zope.formlib.form import FormFields
from zope.schema import Choice, TextLine
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary

from canonical.widgets import PasswordChangeWidget

from canonical.launchpad import _
from canonical.launchpad.interfaces.account import IAccount
from canonical.launchpad.interfaces.authtoken import (
    IAuthTokenSet, LoginTokenType)
from canonical.launchpad.interfaces.emailaddress import (
    EmailAddressStatus, IEmailAddress, IEmailAddressSet)
from canonical.launchpad.interfaces.launchpad import (
    ILaunchBag, IOpenIDApplication, IPasswordEncryptor)
from canonical.launchpad.validators.email import valid_email
from lp.registry.interfaces.person import (
    IPersonSet, IPersonChangePassword, ITeam)
from canonical.launchpad.webapp import (
    action, canonical_url, custom_widget, LaunchpadEditFormView,
    LaunchpadFormView)
from canonical.launchpad.webapp.menu import structured
from canonical.widgets import LaunchpadRadioWidget


class AccountEditView(LaunchpadEditFormView):
    """Edit account details."""

    schema = IAccount
    label = 'Change your personal details'
    field_names = ["displayname"]
    next_url = '/'

    def __init__(self, context, request):
        super(AccountEditView, self).__init__(self.account, request)

    @action('Change', name='change')
    def change_action(self, action, data):
        """Update the account details."""
        self.updateContextFromData(data)


class AccountPasswordEditView(LaunchpadFormView):
    """Change the account's password."""

    schema = IPersonChangePassword
    label = 'Change your password'
    next_url = '/'
    field_names = ['currentpassword', 'password']
    custom_widget('password', PasswordChangeWidget)

    def __init__(self, context, request):
        super(AccountPasswordEditView, self).__init__(self.account, request)

    def validate(self, data):
        currentpassword = data.get('currentpassword')
        encryptor = getUtility(IPasswordEncryptor)
        if not encryptor.validate(currentpassword, self.context.password):
            self.setFieldError('currentpassword', _(
                "The provided password doesn't match your current password."))

    @action(_("Change"), name="submit")
    def submit_action(self, action, data):
        self.context.password = data['password']


class AccountEditEmailsView(LaunchpadFormView):
    """A view for editing an account's email settings.

    The user can associate emails with their account, verify emails
    the system associated with their account, and remove associated
    emails.
    """

    schema = IEmailAddress

    custom_widget('VALIDATED_SELECTED', LaunchpadRadioWidget,
                  orientation='vertical')
    custom_widget('UNVALIDATED_SELECTED', LaunchpadRadioWidget,
                  orientation='vertical')

    def __init__(self, context, request):
        super(AccountEditEmailsView, self).__init__(self.account, request)

    def setUpFields(self):
        """Set up fields for this view.

        The main fields of interest are the selection fields with custom
        vocabularies for the lists of validated and unvalidated email
        addresses.
        """
        super(AccountEditEmailsView, self).setUpFields()
        self.form_fields = (self._validated_emails_field() +
                            self._unvalidated_emails_field() +
                            FormFields(TextLine(__name__='newemail',
                                                title=u'Add a new address')))

    @property
    def initial_values(self):
        """Set up default values for the radio widgets.

        A radio widget must have a selected value, so we select the
        first unvalidated and validated email addresses in the lists
        to be the default for the corresponding widgets.

        The only exception is if the user has a preferred email
        address: then, that address is used as the default validated
        email address.
        """
        # Defaults for the user's email addresses.
        validated = self.context.preferredemail
        if validated is None:
            validated = self.context.validated_emails.first()
        unvalidated = self.unvalidated_addresses
        if len(unvalidated) > 0:
            # Pick one address from the unvalidated set.
            unvalidated = iter(unvalidated).next()
        return dict(VALIDATED_SELECTED=validated,
                    UNVALIDATED_SELECTED=unvalidated)

    def _validated_emails_field(self):
        """Create a field with a vocabulary of validated emails.

        :return: A Choice field containing the list of validated emails
        """
        terms = [SimpleTerm(term, term.email)
                 for term in self.context.validated_emails]
        preferred = self.context.preferredemail
        if preferred:
            terms.insert(0, SimpleTerm(preferred, preferred.email))

        return FormFields(
            Choice(__name__='VALIDATED_SELECTED',
                   title=_('These addresses are confirmed as being yours'),
                   source=SimpleVocabulary(terms),
                   ),
            custom_widget = self.custom_widgets['VALIDATED_SELECTED'])

    def _unvalidated_emails_field(self):
        """Create a field with a vocabulary of unvalidated and guessed emails.

        :return: A Choice field containing the list of emails
        """
        terms = []
        for term in self.unvalidated_addresses:
            if isinstance(term, unicode):
                term = SimpleTerm(term)
            else:
                term = SimpleTerm(term, term.email)
            terms.append(term)
        if self.validated_addresses:
            title = _('These addresses may also be yours')
        else:
            title = _('These addresses may be yours')

        return FormFields(
            Choice(__name__='UNVALIDATED_SELECTED', title=title,
                   source=SimpleVocabulary(terms)),
            custom_widget = self.custom_widgets['UNVALIDATED_SELECTED'])

    def _validate_selected_address(self, data, field='VALIDATED_SELECTED'):
        """A generic validator for this view's actions.

        Makes sure one (and only one) email address is selected and that
        the selected address belongs to the context person. The address may
        be represented by an EmailAddress object or (for unvalidated
        addresses) an AuthToken object.
        """
        self.validate_widgets(data, [field])

        email = data.get(field)
        if email is None:
            return None
        elif isinstance(data[field], list):
            self.addError("You must not select more than one address.")
            return None

        # Make sure the selected address or login token actually
        # belongs to this account.
        if IEmailAddress.providedBy(email):
            account = email.account

            assert account == self.context, (
                "differing ids in emailaddress.account.id(%s,%d) == "
                "self.context.id(%s,%d) (%s)"
                % (account.displayname, account.id, self.context.displayname,
                   self.context.id, email.email))
        elif isinstance(email, unicode):
            tokenset = getUtility(IAuthTokenSet)
            email = tokenset.searchByEmailAccountAndType(
                email, self.context, LoginTokenType.VALIDATEEMAIL)
            assert email is not None, "Couldn't find login token!"
        else:
            raise AssertionError("Selected address was not EmailAddress "
                                 "or unicode string!")

        # Return the EmailAddress/AuthToken object for use in any
        # further validation.
        return email

    @property
    def validated_addresses(self):
        """All of this person's validated email addresses, including
        their preferred address (if any).
        """
        addresses = []
        if self.context.preferredemail:
            addresses.append(self.context.preferredemail)
        addresses += [email for email in self.context.validated_emails]
        return addresses

    @property
    def unvalidated_addresses(self):
        """All of this person's unvalidated and guessed emails.

        The guessed emails will be EmailAddress objects, and the
        unvalidated emails will be unicode strings.
        """
        emailset = set(self.context.getUnvalidatedEmails())
        emailset = emailset.union(
            [guessed for guessed in self.context.guessed_emails
             if not guessed.email in emailset])
        return emailset

    # Actions to do with validated email addresses.

    def validate_action_remove_validated(self, action, data):
        """Make sure the user selected an email address to remove."""
        emailaddress = self._validate_selected_address(
            data, 'VALIDATED_SELECTED')
        if emailaddress is None:
            return self.errors

        if self.context.preferredemail == emailaddress:
            self.addError(
                "You can't remove %s because it's your contact email "
                "address." % self.context.preferredemail.email)
            return self.errors

        # XXX 2009-06-06 jamesh bug=371567: We don't support deletion
        # of email addresses yet, as EmailAddress.destroySelf() still
        # touches tables the SSO server has no access to.
        self.addError(
            "Can not remove email addresses here yet.")

        return self.errors

    @action(_("Remove"), name="remove_validated",
            validator=validate_action_remove_validated)
    def action_remove_validated(self, action, data):
        """Delete the selected (validated) email address."""
        emailaddress = data['VALIDATED_SELECTED']
        emailaddress.destroySelf()
        self.request.response.addInfoNotification(
            "The email address '%s' has been removed." % emailaddress.email)
        self.next_url = self.action_url

    def validate_action_set_preferred(self, action, data):
        """Make sure the user selected an address."""
        emailaddress = self._validate_selected_address(
            data, 'VALIDATED_SELECTED')
        if emailaddress is None:
            return self.errors

        if emailaddress.status == EmailAddressStatus.PREFERRED:
            self.request.response.addInfoNotification(
                "%s is already set as your contact address." % (
                    emailaddress.email))
        return self.errors

    @action(_("Set as Contact Address"), name="set_preferred",
            validator=validate_action_set_preferred)
    def action_set_preferred(self, action, data):
        """Set the selected email as preferred for the person in context."""
        emailaddress = data['VALIDATED_SELECTED']
        if emailaddress.status != EmailAddressStatus.PREFERRED:
            self.context.setPreferredEmail(emailaddress)
            self.request.response.addInfoNotification(
                "Your contact address has been changed to: %s" % (
                    emailaddress.email))
        self.next_url = self.action_url

    # Actions to do with unvalidated email addresses.

    def validate_action_confirm(self, action, data):
        """Make sure the user selected an email address to confirm."""
        self._validate_selected_address(data, 'UNVALIDATED_SELECTED')
        return self.errors

    @action(_('Confirm'), name='validate', validator=validate_action_confirm)
    def action_confirm(self, action, data):
        """Mail a validation URL to the selected email address."""
        email = data['UNVALIDATED_SELECTED']
        if IEmailAddress.providedBy(email):
            email = email.email
        token = getUtility(IAuthTokenSet).new(
            self.context, getUtility(ILaunchBag).login, email,
            LoginTokenType.VALIDATEEMAIL,
            canonical_url(getUtility(IOpenIDApplication)))
        token.sendEmailValidationRequest()
        self.request.response.addInfoNotification(
            "An e-mail message was sent to '%s' with "
            "instructions on how to confirm that "
            "it belongs to you." % email)
        self.next_url = self.action_url

    def validate_action_remove_unvalidated(self, action, data):
        """Make sure the user selected an email address to remove."""
        email = self._validate_selected_address(data, 'UNVALIDATED_SELECTED')
        if email is not None and IEmailAddress.providedBy(email):
            assert self.context.preferredemail.id != email.id
        return self.errors

    @action(_("Remove"), name="remove_unvalidated",
            validator=validate_action_remove_unvalidated)
    def action_remove_unvalidated(self, action, data):
        """Delete the selected (un-validated) email address.

        This selected address can be either on the EmailAddress table
        marked with status NEW, or in the AuthToken table.
        """
        emailaddress = data['UNVALIDATED_SELECTED']
        if IEmailAddress.providedBy(emailaddress):
            emailaddress.destroySelf()
            email = emailaddress.email
        elif isinstance(emailaddress, unicode):
            getUtility(IAuthTokenSet).deleteByEmailAccountAndType(
                emailaddress, self.context, LoginTokenType.VALIDATEEMAIL)
            email = emailaddress
        else:
            raise AssertionError("Selected address was not EmailAddress "
                                 "or Unicode string!")

        self.request.response.addInfoNotification(
            "The email address '%s' has been removed." % email)
        self.next_url = self.action_url

    # Actions to do with new email addresses

    def validate_action_add_email(self, action, data):
        """Make sure the user entered a valid email address.

        The email address must be syntactically valid and must not already
        be in use.
        """
        has_errors = bool(self.validate_widgets(data, ['newemail']))
        if has_errors:
            # We know that 'newemail' is empty.
            return self.errors

        newemail = data['newemail']
        if not valid_email(newemail):
            self.addError(
                "'%s' doesn't seem to be a valid email address." % newemail)
            return self.errors

        email = getUtility(IEmailAddressSet).getByEmail(newemail)
        account = self.context
        if email is not None:
            if email.account == account:
                if email.status in [EmailAddressStatus.VALIDATED,
                                    EmailAddressStatus.PREFERRED]:
                    self.addError(
                        "The email address '%s' is already registered as "
                        "your email address." % newemail)
            elif email.personID is not None:
                # We can't look up the reference directly, since email
                # addresses and person objects come from different
                # stores.
                owner = getUtility(IPersonSet).get(email.personID)
                owner_name = urllib.quote(owner.name)
                merge_url = (
                    '%s/+requestmerge?field.dupeaccount=%s'
                    % (canonical_url(getUtility(IPersonSet),
                                     rootsite='mainsite'), owner_name))
                if ITeam.providedBy(owner):
                    self.addError(
                        structured(
                            "The email address '%s' is already registered "
                            'to the Launchpad team <a href="%s">%s</a>.',
                            newemail, canonical_url(owner),
                            owner.browsername))
                else:
                    self.addError(
                        structured(
                            "The email address '%s' is already registered "
                            'to <a href="%s">%s</a>. If you think that is a '
                            'duplicated account, you can <a href="%s">merge '
                            "it </a> into your account.",
                            newemail, canonical_url(owner), owner.browsername,
                            merge_url))
            else:
                # There is no way to merge accounts that don't use
                # Launchpad.
                self.addError(
                    "The email address '%s' is registered to another user."
                    % (newemail,))
        return self.errors

    @action(_("Add"), name="add_email", validator=validate_action_add_email)
    def action_add_email(self, action, data):
        """Register a new email for the person in context."""
        newemail = data['newemail']
        token = getUtility(IAuthTokenSet).new(
            self.context, getUtility(ILaunchBag).login, newemail,
            LoginTokenType.VALIDATEEMAIL,
            canonical_url(getUtility(IOpenIDApplication)))
        token.sendEmailValidationRequest()

        self.request.response.addInfoNotification(
                "A confirmation message has been sent to '%s'. "
                "Follow the instructions in that message to confirm that the "
                "address is yours. "
                "(If the message doesn't arrive in a few minutes, your mail "
                "provider might use 'greylisting', which could delay the "
                "message for up to an hour or two.)" % newemail)
        self.next_url = self.action_url
