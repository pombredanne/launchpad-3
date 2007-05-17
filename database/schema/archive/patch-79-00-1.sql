SET client_min_messages=ERROR;

-- Required for shipit admin reports
CREATE INDEX shippingrequest__recipientdisplayname__idx
    ON ShippingRequest(recipientdisplayname);

-- Shrink index
DROP INDEX person_teamowner_idx;
CREATE INDEX person__teamowner__idx ON Person(teamowner)
    WHERE teamowner IS NOT NULL;
DROP INDEX person_merged_idx;
CREATE INDEX person__merged__idx ON Person(merged)
    WHERE merged IS NOT NULL;

-- Indexes required for code.beta.lauchpad.net to not timeout
CREATE INDEX branch__last_scanned__owner__idx ON Branch(last_scanned, owner)
    WHERE last_scanned IS NOT NULL;
CREATE INDEX branch__date_created__idx ON Branch(date_created);

INSERT INTO LaunchpadDatabaseRevision VALUES (79, 0, 1);

