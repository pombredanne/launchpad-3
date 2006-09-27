SET client_min_messages=ERROR;

ALTER TABLE Person ADD COLUMN creation_rationale integer;
ALTER TABLE Person ADD COLUMN creation_comment text;

-- The below commands are to speed up the update of Person.creation_rationale
-- of existing unvalidated profiles.
SELECT Person.id INTO TEMPORARY TABLE InvalidOnes
FROM Person LEFT OUTER JOIN ValidPersonOrTeamCache
    ON Person.id=ValidPersonOrTeamCache.id
WHERE ValidPersonOrTeamCache.id IS NULL;
CREATE INDEX invalidones__id__idx ON InvalidOnes(id);

UPDATE Person SET creation_rationale = 1
FROM InvalidOnes
WHERE InvalidOnes.id = Person.id;

UPDATE Person SET creation_rationale = 8
FROM ValidPersonOrTeamCache
WHERE ValidPersonOrTeamCache.id = Person.id 
    AND Person.teamowner IS NULL;

-- The creation_rationale can be NULL only for teams
ALTER TABLE Person ADD CONSTRAINT creation_rationale_not_null_for_people
    CHECK (creation_rationale IS NULL = teamowner IS NOT NULL);

INSERT INTO LaunchpadDatabaseRevision VALUES (67, 21, 0);

