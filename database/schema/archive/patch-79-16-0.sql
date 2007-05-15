/*
Answer will have an official status to indicate whch products and
distributions are offially use
the Answers application.
*/

SET client_min_messages=ERROR;

ALTER TABLE Product
    ADD COLUMN official_answers BOOLEAN DEFAULT False NOT NULL;

ALTER TABLE Distribution
    ADD COLUMN official_answers BOOLEAN DEFAULT False NOT NULL;

-- Ubuntu and Launchpad are known to offially use Answers

UPDATE  Distribution
    SET official_answers = TRUE
    WHERE name = 'ubuntu';

UPDATE Product
    SET official_answers = TRUE
    FROM Project
    WHERE Product.project = Project.id
        AND Project.name = 'launchpad-project';

INSERT INTO LaunchpadDatabaseRevision VALUES (79, 16, 0);
