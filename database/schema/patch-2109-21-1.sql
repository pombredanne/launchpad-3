SET client_min_messages=ERROR;

-- Index for PPA expiry
create index sbpph__dateremoved__idx ON SecureBinaryPackagePublishingHistory(dateremoved) WHERE dateremoved IS NOT NULL;

insert into launchpaddatabaserevision values (2109, 21, 1);

