
/* This is created as a function so the same definition can be used with
    many tables
*/
    
CREATE OR REPLACE FUNCTION valid_name(text) RETURNS boolean AS '
    import re
    name = args[0]
    pat = r"^[a-z0-9][a-z0-9\\+\\.\\-]+$"
    if name is None or re.match(pat, name):
        return True
    return False
' LANGUAGE plpythonu;

/* A plpgsql version of the above Python, as temporary help for installations
    without working plpythonu
*/
SET client_min_messages TO fatal;
CREATE OR REPLACE FUNCTION valid_name(text) RETURNS boolean AS '
DECLARE
    name ALIAS FOR $1;
BEGIN
    IF name IS NULL OR name SIMILAR TO \'^[a-z0-9][a-z0-9\\+\\.\\-]+$\' THEN
        RETURN true;
    END IF;
    RETURN false;
END;
' LANGUAGE plpgsql;
SET client_min_messages TO notice;

COMMENT ON FUNCTION valid_name(text)
    IS 'validate a name.

    Names must contain only lowercase letters, numbers, ., & -. They
    must start with an alphanumeric. They are ASCII only. Names are useful 
    for mneumonic identifiers such as nicknames and as URL components.
    This specification is the same as the Debian product naming policy.

    Note that a valid name might be all integers, so there is a possible
    namespace conflict if URL traversal is possible by name as well as id.';

CREATE OR REPLACE FUNCTION valid_bug_name(text) RETURNS boolean AS '
    import re
    name = args[0]
    pat = r"^[a-z][a-z0-9\\+\\.\\-]+$"
    if name is None or re.match(pat, name):
        return True
    return False
' LANGUAGE plpythonu;

/* A plpgsql version of the above Python, as temporary help for installations
    without working plpythonu
*/
SET client_min_messages TO fatal;
CREATE OR REPLACE FUNCTION valid_bug_name(text) RETURNS boolean AS '
DECLARE
    name ALIAS FOR $1;
BEGIN
    IF name IS NULL OR name SIMILAR TO \'^[a-z][a-z0-9\\+\\.\\-]+$\' THEN
        RETURN true;
    END IF;
    RETURN false;
END;
' LANGUAGE plpgsql;
SET client_min_messages TO notice;

COMMENT ON FUNCTION valid_bug_name(text) IS 'validate a bug name

    As per valid_name, except numeric-only names are not allowed (including
    names that look like floats).';
 
