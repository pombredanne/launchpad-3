SET client_min_messages=ERROR;

ALTER TABLE Archive
    ALTER COLUMN distribution SET NOT NULL,
    ADD COLUMN buildd_secret text,
    ADD COLUMN require_virtualized boolean NOT NULL DEFAULT TRUE;

ALTER TABLE Archive
    ADD CONSTRAINT valid_buildd_secret 
        CHECK ((private = True AND buildd_secret IS NOT NULL) OR
               (private = False));

-- Only PPA is virtualized.
UPDATE Archive
    SET require_virtualized = FALSE WHERE purpose != 2;

-- The old version of this key was erroneously using owner!=NULL to mean
-- a PPA.
DROP INDEX archive__distribution__purpose__key;
CREATE UNIQUE INDEX archive__distribution__purpose__key
    ON Archive (distribution, purpose) WHERE purpose!=2;

-- Allow the same owner to be set multiply on non-PPA archives.
DROP INDEX archive__owner__key;
CREATE UNIQUE INDEX archive__owner__key
    ON Archive (owner) WHERE purpose=2;

-- And we need a new index for people merge now it can no longer
-- use archive__owner__key
CREATE INDEX archive__owner__idx ON Archive (owner);


-- Add the "virtualized" column which is to replace "trusted".
-- Its logical meaning is the opposite.
ALTER TABLE Builder RENAME COLUMN trusted TO virtualized;
ALTER TABLE Builder ALTER COLUMN virtualized SET DEFAULT TRUE;
UPDATE Builder SET virtualized = NOT virtualized;

INSERT INTO LaunchpadDatabaseRevision VALUES (121, 25, 0);
