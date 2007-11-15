SET client_min_messages=ERROR;

-- Add registrants to both BugBranch and SpecificationBranch links.

ALTER TABLE BugBranch
    ADD COLUMN registrant INT REFERENCES Person;

ALTER TABLE SpecificationBranch
    ADD COLUMN registrant INT REFERENCES Person;

-- Initially populate the registrant as the owner of the branch.
-- It won't be entirely accurate, especially for branches where
-- the branch is owned by a team, but it does give us a starting
-- set.

UPDATE BugBranch
SET registrant=Branch.owner
FROM Branch
WHERE Branch.id = BugBranch.branch;

UPDATE SpecificationBranch
SET registrant=Branch.owner
FROM Branch
WHERE Branch.id = SpecificationBranch.branch;

-- Now add the NOT NULL constraints.

ALTER TABLE BugBranch
    ALTER COLUMN registrant SET NOT NULL;

ALTER TABLE SpecificationBranch
    ALTER COLUMN registrant SET NOT NULL;

-- Need indexes for people merge
CREATE INDEX bugbranch__registrant__idx ON BugBranch(registrant);
CREATE INDEX specificationbranch__registrant__idx
    ON SpecificationBranch(registrant);

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 20, 0);
