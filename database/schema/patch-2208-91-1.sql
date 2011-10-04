-- Copyright 2011 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE OR REPLACE FUNCTION initialise_transitively_private() RETURNS TRIGGER
LANGUAGE plpgsql VOLATILE AS
$$
BEGIN
    NEW.transitively_private := COALESCE(NEW.private, FALSE);
    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION initialise_transitively_private() IS
    'Trigger ensuring the initial value of the Branch transitively_private column is not null';

CREATE TRIGGER check_branch_transitive_privacy_t
    BEFORE INSERT ON Branch
    FOR EACH ROW
    EXECUTE PROCEDURE initialise_transitively_private();

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 91, 1);
