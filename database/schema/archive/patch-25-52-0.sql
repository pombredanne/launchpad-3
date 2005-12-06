
set client_min_messages=ERROR;

/* add an estimate of the number of man-days to deliver this functionality
   */

ALTER TABLE Specification ADD COLUMN man_days integer;

/* Add an estimate of the delivery risk of getting a feature into a
 * distrorelease or product series */

ALTER TABLE Specification ADD COLUMN delivery integer;
UPDATE Specification SET delivery = 0;
ALTER TABLE Specification ALTER COLUMN delivery
    SET DEFAULT 0;
ALTER TABLE Specification ALTER COLUMN delivery SET NOT NULL;

/* allow multiple people to request feedback from someone about the same
 * spec */

ALTER TABLE SpecificationReview
    DROP CONSTRAINT specificationreview_spec_reviewer_uniq;
ALTER TABLE SpecificationReview
    ADD CONSTRAINT unique_spec_requestor_provider
    UNIQUE (specification, requestor, reviewer);


INSERT INTO LaunchpadDatabaseRevision VALUES (25,52,0);
