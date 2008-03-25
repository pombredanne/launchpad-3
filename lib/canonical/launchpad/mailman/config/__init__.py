# Copyright 2007 Canonical Ltd.  All rights reserved.

"""ZConfig datatypes for <mailman> and <mailman-build> configuration keys."""


import os
import grp
import pwd
import random
import socket

from string import ascii_letters, digits

__all__ = [
    'configure_hostname',
    'configure_prefix',
    'configure_siteowner',
    'configure_smtp',
    'configure_usergroup',
    ]


EMPTY_STRING = ''


def configure_hostname(value):
    """Accept a string, but if empty, return the fqdn of the host.

    If a hostname is specified in the config file and it's not the empty
    string, then whatever was used is returned unchanged.

    >>> configure_hostname('myhost.example.com')
    'myhost.example.com'

    Notice also that no attempt is made to make a hostname fully qualified if
    it is not already so.

    >>> configure_hostname('myhost')
    'myhost'

    But if the string is empty, as is the default, then the current host's
    fully qualified domain name is returned, or rather whatever is given by
    socket.getfqdn() is returned (on improperly configured machines, this may
    not actually be fully qualified).

    >>> import socket
    >>> configure_hostname('') == socket.getfqdn()
    True
    """
    if value:
        return value
    return socket.getfqdn()


def configure_prefix(value):
    """Specify Mailman's configure's --prefix argument.

    If a value is given we assume it's a path and make it absolute.  If it's
    already absolute, it doesn't change.

    >>> configure_prefix('/tmp/var/mailman')
    '/tmp/var/mailman'

    If it's relative, then it's relative to the current working directory.

    >>> import os
    >>> here = os.getcwd()
    >>> configure_prefix('some/lib/mailman') == os.path.join(
    ...     here, 'some/lib/mailman')
    True

    If the empty string is given (the default), then this returns lib/mailman
    relative to the current working directory.

    >>> configure_prefix('') == os.path.join(here, 'lib/mailman')
    True
    """
    if value:
        return os.path.abspath(value)
    return os.path.abspath(os.path.join('lib', 'mailman'))


def configure_usergroup(value):
    """Turn a string of the form user:group into the user and group names.

    Given a value, it must be a user and group separated by a colon:

    >>> configure_usergroup('foo')
    Traceback (most recent call last):
    ...
    ValueError: need more than 1 value to unpack
    >>> configure_usergroup('person:group')
    ('person', 'group')

    Numeric values are accepted too, but they are ''not'' converted.

    >>> configure_usergroup('25:26')
    ('25', '26')

    If an empty string is given (the default), then the current user and group
    is returned.

    >>> import pwd, grp
    >>> user, group = configure_usergroup('')
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
    """Return a random string of characters."""
    chars = digits + ascii_letters
    return EMPTY_STRING.join(random.choice(chars) for c in range(length))


def configure_siteowner(value):
    """Accept a string of the form email:password.

    Given a value, it must be an address and password separated by a colon.

    >>> configure_siteowner('foo')
    Traceback (most recent call last):
    ...
    ValueError: need more than 1 value to unpack
    >>> configure_siteowner('me@example.com:password')
    ('me@example.com', 'password')

    However, the format (or validity) of the email address is not checked.

    >>> configure_siteowner('email:password')
    ('email', 'password')

    If an empty string is given (the default), we use a random password and a
    random local part, with the domain forced to example.com.

    >>> address, password = configure_siteowner('')
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

def configure_smtp(value):
    """Return a 2-tuple of (host, port) from a value like 'host:port'.

    The host is a string, the port is an int.

    >>> configure_smtp('host:25')
    ('host', 25)

    >>> configure_smtp('host')
    ('host', 25)

    >>> configure_smtp('host:port')
    Traceback (most recent call last):
     ...
    ValueError: invalid literal for int(): port
    """
    if ':' in value:
        host, port = value.split(':')
        port = int(port)
    else:
        host = value
        port = 25
    return (host, port)
