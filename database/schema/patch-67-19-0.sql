SET client_min_messages=ERROR;

ALTER TABLE Person ADD COLUMN creation_rationale integer;
ALTER TABLE Person ADD COLUMN creation_comment text;

-- The below commands are to speed up the update of Person.creation_rationale
-- of existing unvalidated profiles.
-- XXX: Should this update be moved into a sql script inside the pending/
-- directory?
SELECT Person.id INTO TEMPORARY TABLE InvalidOnes
FROM Person LEFT OUTER JOIN ValidPersonOrTeamCache
    ON Person.id=ValidPersonOrTeamCache.id
WHERE ValidPersonOrTeamCache.id IS NULL;
CREATE INDEX invalidones__id__idx ON InvalidOnes(id);

UPDATE Person SET creation_rationale = 1
FROM InvalidOnes
WHERE InvalidOnes.id = Person.id;

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 19, 0);

