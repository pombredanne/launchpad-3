
import re
from canonical.launchpad.validators.email import valid_email

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

    if not valid_email(email_addr):
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

