SET client_min_messages=ERROR;

/* Improve the targeting of specifications to distroreleases and product
 * series by allowing for a targetstatus flag which can only be set to
 * "approved" by the people who control that distrorelease or product
 * series.
 */


INSERT INTO LaunchpadDatabaseRevision VALUES (40, 87, 0);

