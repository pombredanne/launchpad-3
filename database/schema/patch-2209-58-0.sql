-- Copyright 2014 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;


-- We could avoid a later step using bigserial as the type, but alas that
-- is implemented as a DEFAULT and causes the table to be rewritten.
ALTER TABLE LibraryFileContent ADD COLUMN _id bigint UNIQUE;

ALTER TABLE LibraryFileAlias ADD COLUMN _content bigint
    REFERENCES LibraryFileContent(_id);

-- LibraryFileContent needs an INSERT trigger, ensuring that new
-- records get a LFC._id matching LFC.id
CREATE FUNCTION lfc_sync_id_t() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    NEW._id := NEW.id;
    RETURN NEW;
END;
$$;

CREATE TRIGGER lfc_sync_id_t BEFORE INSERT ON LibraryFileContent
FOR EACH ROW EXECUTE PROCEDURE lfc_sync_id_t();


-- LibraryFileAlias needs an INSERT and UPDATE trigger, ensuring that
-- LFA.content is synced with LFA._content, and that a corresponding
-- LFC._content exists.
CREATE FUNCTION lfa_sync_content_t() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    NEW._content := NEW.content;
    IF NEW.content IS NOT NULL THEN
        UPDATE LibraryFileContent SET _id=id
        WHERE id = NEW.content and _id IS NULL;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER lfa_sync_content_t BEFORE INSERT OR UPDATE ON LibraryFileAlias
FOR EACH ROW EXECUTE PROCEDURE lfa_sync_content_t();


INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 58, 0);
