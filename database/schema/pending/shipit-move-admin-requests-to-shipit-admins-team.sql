UPDATE ShippingRequest 
SET recipient = (SELECT id FROM Person WHERE name = 'shipit-admins')
WHERE recipient IN (
    SELECT Person 
    FROM TeamParticipation 
    WHERE team = (SELECT id FROM Person WHERE name = 'shipit-admins')
    );
