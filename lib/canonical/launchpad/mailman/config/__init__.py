# Copyright 2007 Canonical Ltd.  All rights reserved.

"""ZConfig datatypes for <mailman> and <mailman-build> configuration keys."""


import os
import grp
import pwd
import random
import socket

from string import ascii_letters, digits

__all__ = [
    'hostname',
    'prefix',
    'siteowner',
    'usergroup',
    ]


EMPTY_STRING = ''


def hostname(value):
    """Accept a string, but if empty, return the fqdn of the host.

    If a hostname is specified in the config file and it's not the empty
    string, then whatever was used is returned unchanged.

    >>> hostname('myhost.example.com')
    'myhost.example.com'

    Notice also that no attempt is made to make a hostname fully qualified if
    it is not already so.

    >>> hostname('myhost')
    'myhost'

    But if the string is empty, as is the default, then the current host's
    fully qualified domain name is returned, or rather whatever is given by
    socket.getfqdn() is returned (on improperly configured machines, this may
    not actually be fully qualified).

    >>> import socket
    >>> hostname('') == socket.getfqdn()
    True
    """
    if value:
        return value
    return socket.getfqdn()


def prefix(value):
    """Specify Mailman's configure's --prefix argument.

    If a value is given we assume it's a path and make it absolute.  If it's
    already absolute, it doesn't change.

    >>> prefix('/tmp/var/mailman')
    '/tmp/var/mailman'

    If it's relative, then it's relative to the current working directory.

    >>> import os
    >>> here = os.getcwd()
    >>> prefix('some/lib/mailman') == os.path.join(here, 'some/lib/mailman')
    True

    If the empty string is given (the default), then this returns lib/mailman
    relative to the current working directory.

    >>> prefix('') == os.path.join(here, 'lib/mailman')
    True
    """
    if value:
        return os.path.abspath(value)
    return os.path.abspath(os.path.join('lib', 'mailman'))


def usergroup(value):
    """Turn a string of the form user:group into the user and group names.

    Given a value, it must be a user and group separated by a colon:

    >>> usergroup('foo')
    Traceback (most recent call last):
    ...
    ValueError: need more than 1 value to unpack
    >>> usergroup('person:group')
    ('person', 'group')

    Numeric values are accepted too, but they are ''not'' converted.

    >>> usergroup('25:26')
    ('25', '26')

    If an empty string is given (the default), then the current user and group
    is returned.

    >>> import pwd, grp
    >>> user, group = usergroup('')
    >>> user == pwd.getpwuid(os.getuid()).pw_name
    True
    >>> group == grp.getgrgid(os.getgid()).gr_name
    True
    """

    # Make sure the target directories exist and have the correct
    # permissions, otherwise configure will complain.
    if value:
        user, group = value.split(':', 1)
    else:
        user  = pwd.getpwuid(os.getuid()).pw_name
        group = grp.getgrgid(os.getgid()).gr_name
    return user, group


def random_characters(length=10):
    # Return a random string of characters.  This is a helper function, not a
    # publicly exposed datatype.
    chars = digits + ascii_letters
    return EMPTY_STRING.join(random.choice(chars) for c in range(length))


def siteowner(value):
    """Accept a string of the form email:password.

    Given a value, it must be an address and password separated by a colon.

    >>> siteowner('foo')
    Traceback (most recent call last):
    ...
    ValueError: need more than 1 value to unpack
    >>> siteowner('me@example.com:password')
    ('me@example.com', 'password')

    However, the format (or validity) of the email address is not checked.

    >>> siteowner('email:password')
    ('email', 'password')

    If an empty string is given (the default), we use a random password and a
    random local part, with the domain forced to example.com.

    >>> address, password = siteowner('')
    >>> len(password) == 10
    True
    >>> localpart, domain = address.split('@', 1)
    >>> len(localpart) == 10
    True
    >>> domain
    'example.com'
    """
    if value:
        addr, password = value.split(':', 1)
    else:
        localpart = random_characters()
        password  = random_characters()
        addr = localpart + '@example.com'
    return addr, password
