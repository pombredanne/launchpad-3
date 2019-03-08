-- Copyright 2014 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;

-- STEP 4, DB PATCH 2.
-- Add the new wide column to LibraryFileAlias, as a foreign key reference
-- to LFC._id
ALTER TABLE LibraryFileAlias
    ADD COLUMN _content bigint REFERENCES LibraryFileContent(_id);

-- LibraryFileAlias needs an INSERT and UPDATE trigger, ensuring that
-- LFA.content is synced with LFA._content. We have already backfilled
-- LFC._id, so we can guarantee inserts will not fail due to FK violation.
CREATE FUNCTION lfa_sync_content_t() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    NEW._content := NEW.content;
    RETURN NEW;
END;
$$;

CREATE TRIGGER lfa_sync_content_t BEFORE INSERT OR UPDATE ON LibraryFileAlias
FOR EACH ROW EXECUTE PROCEDURE lfa_sync_content_t();

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 58, 2);
