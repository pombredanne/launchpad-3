-- Copyright 2014 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE OR REPLACE FUNCTION valid_cve(text) RETURNS boolean
    LANGUAGE plpythonu IMMUTABLE STRICT
    AS $_$
    import re
    name = args[0]
    pat = r"^(19|20)\d{2}-\d{4,}$"
    if re.match(pat, name):
        return 1
    return 0
$_$;

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 55, 0);
