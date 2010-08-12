-- Copyright 2010 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).
SET client_min_messages=ERROR;

-- This function is not STRICT, since it needs to handle
-- dateexpected when it is NULL.
CREATE OR REPLACE FUNCTION milestone_sort_key(
    dateexpected timestamp, name text)
    RETURNS text
AS $_$
    # If this method is altered, then any functional indexes using it
    # need to be rebuilt.
    import re
    import datetime
    import plpy

    date_expected, name = args
    
    def substitude_filled_numbers(match):
        return match.group(0).zfill(5)

    name = re.sub(u'\d+', substitude_filled_numbers, name)
    if date_expected is None:
        # NULL dates are considered to be in the future.
        date_expected = str(datetime.datetime(datetime.MAXYEAR, 1, 1))
    return (date_expected, name)
$_$
LANGUAGE plpythonu IMMUTABLE;

CREATE INDEX milestone_dateexpected_name_sort
ON Milestone
USING btree (milestone_sort_key(dateexpected, name));

INSERT INTO LaunchpadDatabaseRevision VALUES (2207, 99, 0);
