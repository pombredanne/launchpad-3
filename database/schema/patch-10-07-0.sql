SET client_min_messages=ERROR;

/*
  Changes required to implement the TeamMembership spec.
*/

ALTER TABLE Person ADD COLUMN defaultmembershipperiod integer;
ALTER TABLE Person ADD COLUMN defaultrenewalperiod integer; 
ALTER TABLE Person ADD COLUMN subscriptionpolicy integer; 

UPDATE person SET subscriptionpolicy=1;

ALTER TABLE Person ALTER COLUMN subscriptionpolicy SET NOT NULL;
ALTER TABLE Person ALTER COLUMN defaultmembershipperiod SET DEFAULT NULL;
ALTER TABLE Person ALTER COLUMN defaultrenewalperiod SET DEFAULT NULL;
ALTER TABLE Person ALTER COLUMN subscriptionpolicy SET DEFAULT 1;


ALTER TABLE TeamMembership DROP COLUMN role;

ALTER TABLE TeamMembership ADD COLUMN datejoined timestamp without time zone;
ALTER TABLE TeamMembership ADD COLUMN dateexpires timestamp without time zone;
ALTER TABLE TeamMembership ADD COLUMN reviewer integer;
ALTER TABLE TeamMembership ADD COLUMN reviewercomment text;

ALTER TABLE TeamMembership ALTER COLUMN datejoined SET NOT NULL;
ALTER TABLE TeamMembership ALTER COLUMN datejoined SET DEFAULT timezone('UTC'::text, ('now'::text)::timestamp(6) with time zone);
ALTER TABLE TeamMembership ALTER COLUMN dateexpires SET DEFAULT NULL;
ALTER TABLE TeamMembership ADD CONSTRAINT reviewer_fk FOREIGN KEY (reviewer)
REFERENCES Person(id);

INSERT INTO LaunchpadDatabaseRevision VALUES (10, 7, 0);
