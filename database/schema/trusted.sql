
/* This is created as a function so the same definition can be used with
    many tables
*/
    
CREATE OR REPLACE FUNCTION valid_name(text) RETURNS boolean AS '
    import re
    name = args[0]
    pat = r"^[a-z0-9][a-z0-9\\+\\.\\-]+$"
    if name is None or re.match(pat, name):
        return 1
    return 0
' LANGUAGE plpythonu;

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
        return 1
    return 0
' LANGUAGE plpythonu;

COMMENT ON FUNCTION valid_bug_name(text) IS 'validate a bug name

    As per valid_name, except numeric-only names are not allowed (including
    names that look like floats).';


CREATE OR REPLACE FUNCTION valid_version(text) RETURNS boolean AS '
    import re
    name = args[0]
    pat = r"^[A-Za-z0-9\\+:\\.\\-\\~]+$"
    if name is None or re.match(pat, name):
        return 1
    return 0
' LANGUAGE plpythonu;

COMMENT ON FUNCTION valid_version(text) IS 'validate a version number

    Note that this is more flexible than the Debian naming policy,
    as it states ''SHOULD'' rather than ''MUST'', and we have already
    imported packages that don''t match it. Note that versions
    may contain both uppercase and lowercase letters so we can''t use them
    in URLs. Also note that both a product name and a version may contain
    hypens, so we cannot join the product name and the version with a hypen
    to form a unique string (we need to use a space or some other character
    disallowed in the product name spec instead';


CREATE OR REPLACE FUNCTION valid_cve(text) RETURNS boolean AS '
    import re
    name = args[0]
    pat = r"^(CAN|CVE)-(19|20)\\d\\d-\\d+$"
    if re.match(pat, name):
        return 1
    return 0
' LANGUAGE plpythonu;

COMMENT ON FUNCTION valid_cve(text) IS 'validate a common vulnerability number

    As defined on www.cve.mitre.org';

