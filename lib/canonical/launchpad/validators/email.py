# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""EmailAdress validator"""

__metaclass__ = type

def valid_email(emailaddr):
    import re    
    if re.match(r"^[_\.0-9a-zA-Z-+]+@([0-9a-zA-Z-]{1,}\.)*[a-zA-Z]{2,}$",
                emailaddr):
        return True
    else:
        return False
valid_email.sql_signature = [('email', 'text')]
