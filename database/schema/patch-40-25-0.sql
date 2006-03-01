SET client_min_messages=ERROR;

/* We will no longer have the IMPLEMENTED value for the SpecificationStatus
 * enum, because we will use the Specification.delivery field to track this
 * progress. So we must make sure that all IMPLEMENTED specs get their
 * delivery value set to IMPLEMENTED, and then set all of their drafting
 * status to APPROVED.
 */

UPDATE Specification SET delivery=90, status=10 WHERE status=50;

/* Improve the targeting of specifications to distroreleases and product
 * series by allowing for a goalstatus flag which can only be set to
 * "approved" by the people who control that distrorelease or product
 * series. The default will be PROPOSED (30), and the drivers of the distro
 * release or product series can then ACCEPT or DECLINE the specification.
 */

ALTER TABLE Specification ADD COLUMN goalstatus integer;
ALTER TABLE Specification ALTER COLUMN goalstatus SET DEFAULT 30;
UPDATE Specification SET goalstatus = 30;
ALTER TABLE Specification ALTER COLUMN goalstatus SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 25, 0);

