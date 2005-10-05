# Twisted Application Configuration file.
# Use with "twistd -y <file.tac>", e.g. "twistd -noy server.tac"

from twisted.application import service

from canonical.buildd.sequencer import BuildSequencer

# Construct the application
application = service.Application("BuildSequencer")

class BuildSequencerService(service.Service):
    def __init__(self, buildSequencer):
        self.buildSequencer = buildSequencer
 
    def startService(self):
        # Kick everything off...
        self.buildSequencer.scheduleCallback()
 

# Construct the sequencer. It will automatically schedule the first job.
bseq = BuildSequencer()
# Make a service out of the sequencer
bserv = BuildSequencerService(bseq)

# Activate the service
BuildSequencerService(bseq).setServiceParent(application)

# Falling off the end here passes into twisted's reactor.
