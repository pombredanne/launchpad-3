# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""
Custom Password widgets.

TODO: Consider folding this back into Zope3 -- StuartBishop 20050520
"""

__metaclass__ = type

from zope.app.form.browser import PasswordWidget
from zope.app.form.browser.interfaces import ITextBrowserWidget
from zope.app.form.interfaces import WidgetInputError
from zope.component import getUtility
from zope.interface import implements
from zope.schema.interfaces import ValidationError

from z3c.ptcompat import ViewPageTemplateFile

from canonical.launchpad import _
from canonical.launchpad.interfaces.launchpad import IPasswordEncryptor
from canonical.launchpad.webapp.interfaces import IMultiLineWidgetLayout


class PasswordMismatch(ValidationError):
    __doc__ = _("Passwords do not match.")

    def __repr__(self):
        return repr(self.__doc__)


class RequiredPasswordMissing(ValidationError):
    __doc__ = _("You must enter a password.")

    def __repr__(self):
        return repr(self.__doc__)


class PasswordChangeWidget(PasswordWidget):
    """A password change widget.

    Text is not echoed to the user, and two text boxes are used to ensure
    the password is entered correctly.
    """
    implements(ITextBrowserWidget, IMultiLineWidgetLayout)
    type = 'password change'
    display_label = False

    __call__ = ViewPageTemplateFile('templates/passwordchange.pt')

    def hasInput(self):
        """We always have input if there is an existing value

        No input indicates unchanged.
        """
        if PasswordWidget.hasInput(self):
            return True

        # If we don't have input from the user, we lie because we will
        # use the existing value.
        return bool(self._getCurrentPassword())

    def _getCurrentPassword(self):
        # Yesh... indirection up the wazoo to do something this simple.
        # Returns the current password.
        return self.context.get(self.context.context) or None

    def getInputValue(self):
        """Ensure both text boxes contain the same value and inherited checks

        >>> from canonical.launchpad.webapp.servers import (
        ...     LaunchpadTestRequest)
        >>> from zope.schema import Field
        >>> field = Field(__name__='foo', title=u'Foo')

        The widget will only return a value if both of the text boxes
        contain the same value. It returns the value encrypted.

        >>> request = LaunchpadTestRequest(form={
        ...     'field.foo': u'My Password', 'field.foo_dupe': u'My Password'})
        >>> widget = PasswordChangeWidget(field, request)
        >>> crypted_pw = widget.getInputValue()
        >>> encryptor = getUtility(IPasswordEncryptor)
        >>> encryptor.validate(u'My Password', crypted_pw)
        True

        Otherwise it raises the exception required by IInputWidget

        >>> request = LaunchpadTestRequest(form={
        ...     'field.foo': u'My Password', 'field.foo_dupe': u'No Match'})
        >>> widget = PasswordChangeWidget(field, request)
        >>> widget.getInputValue()
        Traceback (most recent call last):
            [...]
        WidgetInputError: ('foo', u'Foo', u'Passwords do not match.')
        """
        value1 = self.request.form_ng.getOne(self.name, None)
        value2 = self.request.form_ng.getOne('%s_dupe' % self.name, None)
        if value1 != value2:
            self._error = WidgetInputError(
                    self.context.__name__, self.label, PasswordMismatch()
                    )
            raise self._error

        # If the user hasn't entered a password, we use the existing one
        # if it is there. If it is not there, we are creating a new password
        # and we raise an error
        if not value1:
            current_password = self._getCurrentPassword()
            if current_password:
                return current_password
            else:
                self._error = WidgetInputError(
                        self.context.__name__, self.label,
                        RequiredPasswordMissing()
                        )
                raise self._error

        # Do any other validation
        value = PasswordWidget.getInputValue(self)
        assert value == value1, 'Form system has changed'

        # If we have matching plaintext, encrypt it and return the password
        encryptor = getUtility(IPasswordEncryptor)
        return encryptor.encrypt(value)

