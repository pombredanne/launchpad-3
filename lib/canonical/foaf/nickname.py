# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Nickname generation."""

__metaclass__ = type
__all__ = []

import random
import re

from canonical.database.sqlbase import cursor, sqlvalues
from canonical.launchpad.validators.email import valid_email
from canonical.launchpad.validators.name import sanitize_name, valid_name


class NicknameGenerationError(Exception):
    """I get raised when something went wrong generating a nickname."""


def _is_nick_registered(nick):
    """Answer the question: is this nick registered?"""
    # XXX: SteveAlexander 2005-06-12:
    #      This should use IPersonSet.  Before we change this, we need to
    #      make sure that all users of nickname.py are running inside the
    #      launchpad web application, or are using zcml_for_scripts.
    from canonical.launchpad.database import PersonSet
    return PersonSet().getByName(nick) is not None


def is_blacklisted(name, cur=None):
    """Check whether a name is blacklisted by Launchpad Administrators.

    :param name: Unicode string to look for in the table of blacklisted names.
    :param cur: cursor for the open connection; used in a test.
    """
    if cur is None:
        cur = cursor()
    cur.execute("SELECT is_blacklisted_name(%(name)s)" % sqlvalues(
        name=name.encode('UTF-8')))
    return bool(cur.fetchone()[0])


def generate_nick(email_addr, is_registered=_is_nick_registered):
    """Generate a LaunchPad nick from the email address provided.

    See canonical.launchpad.validators.name for the definition of a
    valid nick.

    It is technically possible for this function to raise a
    NicknameGenerationError, but this will only occur if an operator
    has majorly screwed up the name blacklist.
    """
    email_addr = email_addr.strip().lower()

    if not valid_email(email_addr):
        raise NicknameGenerationError("%s is not a valid email address"
                                      % email_addr)

    user, domain = re.match("^(\S+)@(\S+)$", email_addr).groups()
    user = user.replace(".", "-").replace("_", "-")
    domain_parts = domain.split(".")

    def _valid_nick(nick):
        if not valid_name(nick):
            return False
        elif is_registered(nick):
            return False
        elif is_blacklisted(nick):
            return False
        else:
            return True

    generated_nick = sanitize_name(user)
    if _valid_nick(generated_nick):
        return generated_nick

    for domain_part in domain_parts:
        generated_nick = sanitize_name(generated_nick + "-" + domain_part)
        if _valid_nick(generated_nick):
            return generated_nick

    # We seed the random number generator so we get consistant results,
    # making the algorithm repeatable and thus testable.
    random_state = random.getstate()
    random.seed(sum(ord(letter) for letter in generated_nick))
    try:
        attempts = 0
        prefix = ''
        suffix = ''
        mutated_nick = [letter for letter in generated_nick]
        chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
        while attempts < 1000:
            attempts += 1

            # Prefer a nickname with a suffix
            suffix += random.choice(chars)
            if _valid_nick(generated_nick + '-' + suffix):
                return generated_nick + '-' + suffix

            # Next a prefix
            prefix += random.choice(chars)
            if _valid_nick(prefix + '-' + generated_nick):
                return prefix + '-' + generated_nick

            # Or a mutated character
            index = random.randint(0, len(mutated_nick)-1)
            mutated_nick[index] = random.choice(chars)
            if _valid_nick(''.join(mutated_nick)):
                return ''.join(mutated_nick)

            # Or a prefix + generated + suffix
            if _valid_nick(prefix + '-' + generated_nick + '-' + suffix):
                return prefix + '-' + generated_nick + '-' + suffix

            # Or a prefix + mutated + suffix
            if _valid_nick(
                    prefix + '-' + ''.join(mutated_nick) + '-' + suffix):
                return prefix + '-' + ''.join(mutated_nick) + '-' + suffix

        raise NicknameGenerationError(
            "No nickname could be generated. "
            "This should be impossible to trigger unless some twonk has "
            "registered a match everything regexp in the black list."
            )

    finally:
        random.setstate(random_state)


def generate_wikiname(displayname, registered):
    """Generate a LaunchPad wikiname from the displayname provided.

    e.g.:

        >>> generate_wikiname('Andrew Bennetts', lambda x: False)
        'AndrewBennetts'
        >>> generate_wikiname('andrew bennetts', lambda x: False)
        'AndrewBennetts'
        >>> generate_wikiname('Jean-Paul Example', lambda x: False)
        'JeanPaulExample'
        >>> generate_wikiname('Foo Bar', lambda x: x == 'FooBar')
        'FooBar2'
        >>> generate_wikiname(u'Andr\xe9 Lu\xeds Lopes', lambda x: False)
        u'Andr\\xe9Lu\\xedsLopes'

    """
    # First, just try smooshing the displayname together (stripping punctuation
    # and the like), and see if that's free.
    #       -- Andrew Bennetts, 2005-06-14
    wikinameparts = re.split(r'(?u)\W+', displayname)
    wikiname = ''.join([part.capitalize() for part in wikinameparts])
    if not registered(wikiname):
        return wikiname

    # Append a number to uniquify, and keep incrementing it until we succeed.
    counter = 2
    while True:
        candidate = wikiname + str(counter)
        if not registered(candidate):
            return candidate
        counter += 1

