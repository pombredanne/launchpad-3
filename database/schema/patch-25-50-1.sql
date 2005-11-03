set client_min_messages=error;

create index shippingrequest_cancelled_idx on shippingrequest(cancelled);
create index shippingrequest_recipient_cancelled_idx
    on shippingrequest(recipient, cancelled);

insert into launchpaddatabaserevision values (25, 50, 1);
