
def valid_cve(name):
    import re
    pat = r"^(19|20)\d\d-\d{4}$"
    if re.match(pat, name):
        return True
    return False
    
valid_cve.sql_signature = [
    ('name', 'text'),
    ]

