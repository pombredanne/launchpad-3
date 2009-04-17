# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Helper functions for registering new Launchpad accounts."""

__metaclass__ = type

from canonical.launchpad.ftests import logout
from canonical.launchpad.testing.pages import setupBrowser
from canonical.launchpad.webapp import canonical_url


def start_registration_through_the_web(email):
    """Create a Browser and drive it through the first step of registering a
    new account.

    Return the Browser object after submitting the form.
    """
    logout()
    browser = setupBrowser()
    browser.open('http://launchpad.dev/+login')
    browser.getControl(name='loginpage_email', index=1).value = email
    browser.getControl('Register').click()
    return browser


def finish_registration_through_the_web(token):
    """Create a Browser and drive it through the account registration.

    Return the Browser object after the registration is finished.
    """
    token_url = canonical_url(token)
    logout()
    browser = setupBrowser()
    browser.open(token_url)
    browser.getControl('Name').value = 'New User'
    browser.getControl('Create password').value = 'test'
    browser.getControl(name='field.password_dupe').value = 'test'
    browser.getControl('Continue').click()
    return browser
