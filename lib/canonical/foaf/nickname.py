#!/usr/bin/python

import re

MIN_NICK_LENGTH = 2

class NicknameGenerationError(Exception):
    """I get raised when something went wrong generating
    a nickname."""
    pass

def _nick_registered(nick):
    """Answers the question: is this nick registered?"""
    EXISTING_NICKS = [
        'foop-example', 'spam', 'spam-example', 'turtle', 'taken',
        'taken-example', 'taken-example-com', 'taken-example-com-1',
        'bar-spam', 'bar-spam-long', 'bar-spam-long-example']

    return nick in EXISTING_NICKS

def generate_nick(email_addr, registered=_nick_registered,
                  report_collisions=False):
    """Generate a LaunchPad nick from the email address provided.

    A valid nick can contain lower case letters, dashes, and numbers,
    must start with a letter or a number, and must be a minimum of
    four characters.

    >>> generate_nick("foop@example@com")
    Traceback (most recent call last):
        ...
    NicknameGenerationError: foop@example@com is not a valid email address
    >>> generate_nick("foop@example.com")
    'foop'
    >>> generate_nick("bar@example.com")
    'bar'
    >>> generate_nick("spam@example.com")
    'spam-example-com'
    >>> generate_nick("foop.bar@example.com")
    'foop-bar'
    >>> generate_nick("bar.spam@long.example.com")
    'bar-spam-long-example-com'
    >>> generate_nick("taken@example.com")
    'taken-example-com-2'
    >>> generate_nick("taken@example")
    'taken-example-1'
    >>> generate_nick("i@tv")
    'i-tv'
    >>> generate_nick("foo+bar@example.com")
    'foo+bar'
    """

    from canonical.auth.browser import well_formed_email

    email_addr = email_addr.strip().lower()

    if not well_formed_email(email_addr):
        raise NicknameGenerationError("%s is not a valid email address" 
                                      % email_addr)

    user, domain = re.match("^(\S+)@(\S+)$", email_addr).groups()
    user = user.replace(".", "-").replace("_", "-")
    domain_parts = domain.split(".")

    generated_nick = user
    if (registered(generated_nick) or 
        len(generated_nick) < MIN_NICK_LENGTH):
        if report_collisions:
            print ("collision: %s already registered or shorter than 4 "
                   "characters." % generated_nick)

        for domain_part in domain_parts:
            generated_nick += "-" + domain_part
            if not registered(generated_nick):
                break
            else:
                if report_collisions:
                    print "collision: %s already registered" % generated_nick

    if not generated_nick:
        raise NicknameGenerationError("no nickname could be generated")

    if (registered(generated_nick) 
        or len(generated_nick) < MIN_NICK_LENGTH):
        if report_collisions:
            print ("collision: %s already registered or shorter than 4 "
                   "characters" % generated_nick)

        x = 1
        found_available_nick = False
        while not found_available_nick:
            attempt = generated_nick + "-" + str(x)
            if not registered(attempt):
                generated_nick = attempt
                break
            else:
                if report_collisions:
                    print "collision: %s already registered" % generated_nick

            x += 1

    return generated_nick

def _test():
    import doctest, nickname
    return doctest.testmod(nickname)

if __name__ == '__main__':
    _test()

