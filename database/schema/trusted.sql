
/* This is created as a function so the same definition can be used with
    many tables
*/
    
CREATE OR REPLACE FUNCTION valid_name(text) RETURNS boolean AS '
    """validate a name
    
    Names must contain only lowercase letters, numbers, ., _ * -.
    They must contain at least one non-digit to avoid namespace conflicts
    with integer ids. They are ASCII only. Names are useful for mneumonic
    identifiers such as nicknames and as URL components.

    """
    import re
    name = args[0]
    pat = r"^[a-z0-9_\\.\\-]*[a-z_\\.\\-][a-z0-9_\\.\\-]*$"
    if name is None or re.match(pat, name):
        return True
    return False
' LANGUAGE plpythonu;

COMMENT ON FUNCTION valid_name(text)
    IS 'validate a name.

    Names must contain only lowercase letters, numbers, ., _ * -.
    They must contain at least one non-digit to avoid namespace conflicts
    with integer ids. They are ASCII only. Names are useful for mneumonic
    identifiers such as nicknames and as URL components.';

