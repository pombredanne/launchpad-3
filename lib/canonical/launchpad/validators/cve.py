
def valid_cve(name):
    import re
    pat = r"^(CAN|CVE)-(19|20)\d\d-\d+$"
    if re.match(pat, name):
        return True
    return False
    
valid_cve.sql_signature = [
    ('name', 'text'),
    ]

