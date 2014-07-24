-- Copyright 2014 Canonical Ltd.  This software is licensed under the
-- GNU Affero General Public License version 3 (see the file LICENSE).

SET client_min_messages=ERROR;


ALTER TABLE LibraryFileContent ADD COLUMN _id bigint;
ALTER TABLE LibraryFileAlias ADD COLUMN _content bigint;

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

/* Subsequent statements, to be executed live and in subsequent patches
   after timing and optimization. */


/*
-- STEP 2 -- Fill in new columns, not a DB patch.
--DROP TRIGGER lfa_sync_content_t ON LibraryFileAlias;
--DROP TRIGGER lfc_sync_id_t ON LibraryFileContent;
UPDATE LibraryFileAlias SET _content = content;
UPDATE LibraryFileContent SET _id = id;


-- STEP 3 -- Indexes, to be built concurrently.
CREATE UNIQUE INDEX libraryfilecontent_id_key ON LibraryFileContent(_id);
CREATE INDEX libraryfilealias__content__idx ON LibraryFileAlias(_content);
CREATE INDEX libraryfilealias__expires_has_content__idx
    ON LibraryFileAlias(expires) WHERE content IS NOT NULL;

DROP INDEX LibraryFileAlias__expires__idx; -- Confirm this index is unused.


-- STEP 4 -- Constraints, swap into place, and the rest. May be split.
DROP TRIGGER lfa_sync_content_t ON LibraryFileAlias;
DROP TRIGGER lfc_sync_id_t ON LibraryFileContent;
DROP FUNCTION lfa_sync_content_t();
DROP FUNCTION lfc_sync_id_t();

ALTER SEQUENCE libraryfilecontent_id_seq OWNED BY LibraryFileContent._id;

ALTER TABLE LibraryFileAlias DROP COLUMN content;
ALTER TABLE LibraryFileAlias RENAME _content TO content;
ALTER TABLE LibraryFileContent DROP COLUMN id;
ALTER TABLE LibraryFileContent RENAME _id TO id;

ALTER INDEX libraryfilecontent_id_key RENAME TO libraryfilecontent_pkey;
ALTER TABLE LibraryFileContent
    ALTER COLUMN id SET DEFAULT nextval('libraryfilecontent_id_seq'),
    ALTER COLUMN id SET NOT NULL,  -- Slow
    ALTER COLUMN sha256 SET NOT NULL, -- Slow
    ADD CONSTRAINT libraryfilecontent_pkey
        PRIMARY KEY USING INDEX libraryfilecontent_pkey; -- Maybe slow.

ALTER TABLE LibraryFileAlias ADD CONSTRAINT libraryfilealias__content__fkey
    FOREIGN KEY (content) REFERENCES LibraryFileContent(id); -- Slow
*/

INSERT INTO LaunchpadDatabaseRevision VALUES (2209, 58, 0);
