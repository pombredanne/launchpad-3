SET client_min_messages=ERROR;

/* Blueprint Updates
   A series of small fixes to the Blueprint data model to address minor
   issues that have arisen since the Edgy sprint in Paris.
*/

  -- Allow for recording if someone is essential to a spec discussions
ALTER TABLE SpecificationSubscription ADD COLUMN essential boolean;
UPDATE SpecificationSubscription SET essential=FALSE;
ALTER TABLE SpecificationSubscription ALTER COLUMN essential SET DEFAULT False; 
ALTER TABLE SpecificationSubscription ALTER COLUMN essential SET NOT NULL; 


INSERT INTO LaunchpadDatabaseRevision VALUES (67, 97, 0);
