window.SignalWrapper = new function() {
    /* wraps MochiKit's Signal stuff and keeps a small registry of
        registered events, so that cleaning up on unload is 
        comparatively easy
    */
    
    var registry = {};
    var nextid = 0;

    this.connect = function(src, signal, dest, func) {
        var id = nextid++;
        registry[id] = [src, signal, dest, func];
        MochiKit.Signal.connect(src, signal, dest, func);
        return id;
    };

    this.disconnect = function(id) {
        /* deregister a signal */
        var data = registry[id];
        MochiKit.Signal.disconnect(data[0], data[1], data[2], data[3]);
        delete registry[id];
    };

    this.disconnect_all = function() {
        /* deregister all signals */
        var i=0;
        for (var id in registry) {
            var data = registry[id];
            try {
                MochiKit.Signal.disconnect(data[0], data[1], 
                                            data[2], data[3]);
                i++;
            } catch(e) {
                // ignore problems here...
            };
        };
        registry = {};
    };
}();
