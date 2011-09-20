-- Copyright 2011 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE OR REPLACE FUNCTION maintain_transitively_private() RETURNS TRIGGER
LANGUAGE plpgsql VOLATILE AS
$$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        IF (NEW.stacked_on IS NOT DISTINCT FROM OLD.stacked_on
            AND NEW.private IS NOT DISTINCT FROM OLD.private) THEN
            RETURN NULL;
        END IF;
    END IF;
    PERFORM update_transitively_private(NEW.id);
    RETURN NULL;
END;
$$;

COMMENT ON FUNCTION maintain_transitively_private() IS
    'Trigger maintaining the Branch transitively_private column';

CREATE TRIGGER maintain_branch_transitive_privacy_t
    AFTER INSERT OR UPDATE ON Branch
    FOR EACH ROW
    EXECUTE PROCEDURE maintain_transitively_private();

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 87, 1);
