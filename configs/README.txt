This directory stores configs. The config used is selected on startup
using the LPCONFIG environment variable.

Each config directory contains a launchpad.conf file, and optionally
a number of .zcml files. These .zcml files are processed as ZCML
overrides allowing you to change behavior not yet configurable in
launchpad.conf

If you want to create a temporary config, prefix the direcory name with
'+' so that baz treats it as precious and will not attempt to commit it.

If you need to make changes to the production, staging or dogfood configs
make sure you inform the people in charge of those systems. You may wish
to do this if you are adding a new required config option to
launchpad.conf.

-- StuartBishop 20050603
