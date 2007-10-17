SET client_min_messages=ERROR;

-- Tables missing primary key definitions
ALTER TABLE BugBranch ADD CONSTRAINT bugbranch_pkey PRIMARY KEY (id);
ALTER TABLE LoginToken ADD CONSTRAINT logintoken_pkey PRIMARY KEY (id);
ALTER TABLE ScriptActivity ADD CONSTRAINT scriptactivity_pkey PRIMARY KEY (id);
ALTER TABLE SignedCodeOfConduct
    ADD CONSTRAINT signedcodeofconduct_pkey PRIMARY KEY (id);

-- Unwanted and unloved
DROP TABLE BugRelationship;

-- Improve constraints, stoping creation of broken bugs with huge descriptions.
ALTER TABLE Bug DROP CONSTRAINT no_empty_desctiption;
UPDATE Bug SET description=substring(description FOR 50000)
    WHERE char_length(description) > 50000;
ALTER TABLE Bug ADD CONSTRAINT sane_description CHECK (
    ltrim(description) <> '' AND char_length(description) <= 50000
    );

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 13, 0);
