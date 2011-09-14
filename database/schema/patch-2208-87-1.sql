-- Copyright 2011 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

CREATE OR REPLACE FUNCTION branch_transitive_privacy_update() RETURNS TRIGGER
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path TO public AS
$$
DECLARE
    branch_id integer;
BEGIN
    IF TG_OP = 'INSERT' THEN
        branch_id := NEW.id;
    ELSIF TG_OP = 'UPDATE' AND (
            COALESCE(NEW.stacked_on, 0) != COALESCE(OLD.stacked_on, 0) OR
            NEW.private != OLD.private) THEN
        branch_id := NEW.id;
    ELSIF TG_OP = 'DELETE' THEN
        branch_id := OLD.id;
    ELSE
        return NULL;
    END IF;

    RAISE NOTICE 'BRANCH ID IS %', branch_id;

    UPDATE branch SET transitively_private = (
        WITH
        recursive stacked_branches AS
        (
            SELECT branch.id,
                branch.stacked_on,
                cast(private as int) AS private
            FROM branch as selected_branch
            WHERE selected_branch.id = branch.id
            UNION all
            SELECT stacked_branches.id,
                branch.stacked_on,
                cast(branch.private as int) AS private
            FROM stacked_branches, branch
            WHERE stacked_branches.stacked_on = branch.id)
        SELECT
            CASE WHEN sum(private)>0 THEN True
            ELSE False
            END
        FROM stacked_branches
        GROUP BY id
    ) WHERE id IN (
        WITH recursive
        stacked_branches AS (
            SELECT branch.id,
            branch.stacked_on, cast(private as int) AS private
            FROM branch WHERE id = branch_id
            UNION all
            SELECT branch.id,
            stacked_branches.stacked_on,
            cast(stacked_branches.private as int) AS private
            FROM stacked_branches, branch
            WHERE stacked_branches.id = branch.stacked_on)
        SELECT id FROM stacked_branches
    );
    RETURN NULL; -- Ignored - this is an AFTER trigger
END;
$$;

COMMENT ON FUNCTION branch_transitive_privacy_update() IS
    'Trigger maintaining the Branch transitively_private column';

CREATE TRIGGER branch_transitive_privacy_update_t
    AFTER INSERT OR UPDATE ON branch
    FOR EACH ROW
    EXECUTE PROCEDURE branch_transitive_privacy_update();

INSERT INTO LaunchpadDatabaseRevision VALUES (2208, 87, 1);
