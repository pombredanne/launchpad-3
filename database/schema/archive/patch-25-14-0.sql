set client_min_messages=ERROR;

/* we are simplifying subscriptions for bugs, so why not simplify them for
 * bounties too. The subscription will become T/F, based on the existence of
 * a BountySubscription record. Unsubscribing means removing the record,
 * subscribing means creating one. */

ALTER TABLE BountySubscription DROP COLUMN subscription;
ALTER TABLE Bounty DROP COLUMN duration;
ALTER TABLE Bounty ADD COLUMN bountystatus integer;
ALTER TABLE Bounty ALTER COLUMN bountystatus SET DEFAULT 1;
UPDATE Bounty SET bountystatus=1;
UPDATE Bounty SET difficulty=50;
ALTER TABLE Bounty ALTER COLUMN bountystatus SET NOT NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (25,14,0);
