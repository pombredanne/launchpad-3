set client_min_messages=ERROR;

-- Add new field in table Distrorelease, no constraints are required 
-- except the foreign key 

ALTER TABLE DistroRelease ADD COLUMN nominatedarchindep integer;

ALTER TABLE DistroRelease ADD CONSTRAINT 
      distrorelease_nominatedarchindep_fk FOREIGN KEY (nominatedarchindep) 
      REFERENCES DistroArchRelease;


INSERT INTO LaunchpadDatabaseRevision VALUES (25,37,0);