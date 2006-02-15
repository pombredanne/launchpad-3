set client_min_messages=error;

create index product_active_idx on product(active);

-- Ensure the _untriaged partial index is created using
-- WHERE cancelled = FALSE instead of WHERE cancelled IS FALSE,
-- as our queries use ='f' and were not using the existing index
-- due to the difference in SQL between foo IS FALSE and foo = FALSE
-- when foo IS NULL
drop index shippingrequest_daterequested_untriaged;
create index shippingrequest_daterequested_untriaged
    on shippingrequest(daterequested)
    WHERE cancelled = FALSE AND approved IS NULL;

INSERT INTO LaunchpadDatabaseRevision VALUES (40, 17, 2);

