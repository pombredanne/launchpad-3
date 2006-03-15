import os

class Config:
    """Configuration object for the supermirror
    
    The configuration object loads program variables from the environment.
    If the environment variables do not exist then the defaults present
    here are used for the default. Also included is the replace method to
    override a variable during run and test cases.
    """
    vartable = { 'killfile': (str, "/srv/sm-ng/data/supermirror-die"),
                 'masterlock': (str, "/srv/sm-ng/data/masterlock"),
                 'masterlockattempts': (int, 20),
                 'branchesdest': (str, "/srv/sm-ng/mirrors"),
                 'branchlistsource': (str, ("http://gangotri.ubuntu.com:9000/"
                                            "supermirror-pull-list.txt"))
               }
             
    def __init__(self):
        self.reset()
        self.load()

    def reset(self):
        self.variables = {}
        
    def load(self):
        """Replace default program variables from the environment."""
        self.reset()
        for (variable, (val_type, def_val)) in self.vartable.items():
            val = val_type(os.environ.get(variable.upper(), def_val))
            self.variables[variable] = val

    def __getattr__(self, var):
        if self.variables.has_key(var):
            return self.variables[var]
        else:
            raise AttributeError, var
        
config = Config()
