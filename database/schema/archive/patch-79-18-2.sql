SET client_min_messages=ERROR;

-- Add missing foreign key constraint so people merge works correctly
ALTER TABLE ONLY pomsgset
    ADD CONSTRAINT "pomsgset__person__fk" FOREIGN KEY (reviewer) 
        REFERENCES person(id);

INSERT INTO LaunchpadDatabaseRevision VALUES (79, 18, 2);

