/*
Answer will have an official status to indicate whch products and distributions are offially use
the Answers application.
*/

SET client_min_messages=ERROR;

ALTER TABLE Product
    ADD COLUMN official_answers BOOLEAN DEFAULT False;
    
UPDATE Product
    SET official_answers = False;
    
ALTER TABLE Product
    ALTER official_answers SET NOT NULL;
    
ALTER TABLE Distribution
    ADD COLUMN official_answers BOOLEAN DEFAULT False;
    
UPDATE Distribution
    SET official_answers = False;
    
ALTER TABLE Distribution
    ALTER official_answers SET NOT NULL;

-- Ubuntu and Launchpad are known to offially use Answers

UPDATE  Distribution
    SET official_answers = TRUE
    WHERE name = 'ubuntu';

    
UPDATE  Product
    SET official_answers = TRUE
    WHERE name LIKE 'launchpad%';

INSERT INTO LaunchpadDatabaseRevision VALUES (79, 91, 0);
