SET client_min_messages=ERROR;

ALTER TABLE Archive
    ALTER COLUMN distribution SET NOT NULL,
    ADD COLUMN require_virtualised boolean NOT NULL DEFAULT TRUE;

-- Only PPA is virtualised.
UPDATE Archive
    SET require_virtualised = FALSE WHERE purpose != 2;

-- The old version of this key was erroneously using owner!=NULL to mean
-- a PPA.
DROP INDEX archive__distribution__purpose__key;
CREATE UNIQUE INDEX archive__distribution__purpose__key ON Archive
    USING btree (distribution, purpose)
    WHERE purpose!=2;

-- Allow the same owner to be set multiply on non-PPA archives.
DROP INDEX archive__owner__key;
CREATE UNIQUE INDEX archive__owner__key ON Archive
    USING btree (owner)
    WHERE purpose=2;


-- Add the "virtualised" column which is to replace "trusted".
-- Its logical meaning is the opposite.

ALTER TABLE Builder
    ADD COLUMN virtualised boolean NOT NULL DEFAULT TRUE;

UPDATE Builder
    SET virtualised = NOT trusted;

ALTER TABLE Builder
    DROP COLUMN trusted;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 99, 0);

