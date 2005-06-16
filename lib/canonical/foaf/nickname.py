
import re
from canonical.launchpad.helpers import well_formed_email

MIN_NICK_LENGTH = 2
name_sanity_pattern = re.compile(r"^[^a-z0-9]|[^a-z0-9\\+\\.\\-]+")


class NicknameGenerationError(Exception):
    """I get raised when something went wrong generating a nickname."""

def _nick_registered(nick):
    """Answer the question: is this nick registered?"""
    # XXX: This should use IPersonSet.  Before we change this, we need to
    #      make sure that all users of nickname.py are running inside the
    #      launchpad web application, or are using zcml_for_scripts.
    #      SteveAlexander, 2005-06-12
    from canonical.launchpad.database import PersonSet
    return PersonSet().getByName(nick) is not None

def sanitize(name):
    return name_sanity_pattern.sub('', name)

def generate_nick(email_addr, registered=_nick_registered,
                  report_collisions=False):
    """Generate a LaunchPad nick from the email address provided.

    A valid nick can contain lower case letters, dashes, and numbers,
    must start with a letter or a number, and must be a minimum of
    four characters.
    """
    email_addr = email_addr.strip().lower()

    if not well_formed_email(email_addr):
        raise NicknameGenerationError("%s is not a valid email address" 
                                      % email_addr)

    user, domain = re.match("^(\S+)@(\S+)$", email_addr).groups()
    user = user.replace(".", "-").replace("_", "-")
    domain_parts = domain.split(".")

    generated_nick = sanitize(user)
    if (registered(generated_nick) or 
        len(generated_nick) < MIN_NICK_LENGTH):
        if report_collisions:
            print ("collision: %s already registered or shorter than %d "
                   "characters." % ( generated_nick, MIN_NICK_LENGTH ))

        for domain_part in domain_parts:
            generated_nick = sanitize(generated_nick + "-" + domain_part)
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
            print ("collision: %s already registered or shorter than %d "
                   "characters" % ( generated_nick, MIN_NICK_LENGTH ))

        x = 1
        found_available_nick = False
        while not found_available_nick:
            attempt = sanitize(generated_nick + "-" + str(x))
            if not registered(attempt):
                generated_nick = attempt
                break
            else:
                if report_collisions:
                    print "collision: %s already registered" % generated_nick

            x += 1

    return generated_nick
