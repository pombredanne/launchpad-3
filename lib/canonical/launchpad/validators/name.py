
def valid_name(name):
    import re
    name = args[0]
    pat = r"^[a-z0-9][a-z0-9\\+\\.\\-]+$"
    if name is None or re.match(pat, name):
        return True
    return False
valid_name.sql_signature = [
    ('name', 'text'),
    ]

