
def valid_name(name):
    import re
    pat = r"^[a-z0-9][a-z0-9\\+\\.\\-]+$"
    if re.match(pat, name):
        return True
    return False
    
valid_name.sql_signature = [
    ('name', 'text'),
    ]

