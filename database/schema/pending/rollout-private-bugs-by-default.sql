UPDATE product
        SET private_bugs = true
WHERE name = 'landscape'
   OR name = 'redfish'
   OR name = 'hardware-certification'
   OR name = 'canonical-sfi';
