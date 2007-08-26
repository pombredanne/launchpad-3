SET client_min_messages=ERROR;

-- Updating old records to match the current state machine:
-- 6: PENDINGREMOVAL
-- 7: REMOVED
-- turned into:
-- 3: SUPERSEDED

UPDATE SecureSourcePackagePublishingHistory
    SET status = 3 
    WHERE status IN (6, 7);   

UPDATE SecureBinaryPackagePublishingHistory
    SET status = 3 
    WHERE status IN (6, 7);   


INSERT INTO LaunchpadDatabaseRevision VALUES (87, 99, 0);

