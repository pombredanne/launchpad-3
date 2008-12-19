// A re-usable Dynamic DOM updater using the LP.client
LP = (typeof(LP) != "undefined") ? LP : {};
LP.DynamicDomUpdater = (typeof LP.DynamicDomUpdater != "undefined") ? LP.DynamicDomUpdater : null;

YUI().use("node", "plugin", function(Y) {

    /*
     * DomUpdater - a small plugin for updating a DOM subtree.
     *
     * This plugin allows you to write code such as:
     *
     *  my_table.updater.update({total:3, failed: 1})
     */
    var DomUpdater = function(config){
        DomUpdater.superclass.constructor.apply(this, arguments);
    };

    DomUpdater.NAME = 'domupdater';
    DomUpdater.NS = 'updater';

    DomUpdater.ATTRS = {
        /*
         * The dom node to which this plugin instance is attached.
         */
        owner: {
            value: null
        },
        /*
         * The function that updates the owner's dom subtree.
         */
        dom_update_function: {
            valueFn: null
        }
    };

    /* 
     * Extend from Y.Plugin.
     */
    Y.extend(DomUpdater, Y.Plugin, {

        update: function(update_data) {
            Y.log("Updating Dom subtree", "info", "DomUpdater");

            this.get("dom_update_function")(this.get("owner"), update_data);
        }

    });

    /*
     * LPDynamicDomUpdater - a plugin for dynamically updating a DOM subtree.
     *
     * This plugin allows you to write code such as:
     *
     *  my_table.dupdater.update()
     *
     * to fetch data from an external source and update itself.
     */
    LP.DynamicDomUpdater = function(config){
        LP.DynamicDomUpdater.superclass.constructor.apply(this, arguments);
    };
    LP.DynamicDomUpdater.NAME = 'dynamicdomupdater';
    LP.DynamicDomUpdater.NS = 'updater';
    LP.DynamicDomUpdater.ATTRS = {
        /*
         * The uri to use for the LP.get request.
         */
        uri: {
            value: null
        },

        /*
         * The LP api method name (if applicable).
         */
        api_method_name: {
            value: null
        },

        /*
         * The default refresh interval in ms.
         */
        interval: {
            value: 60000
        },

        /*
         * The configuration for the LP client call.
         *
         * If this is not included, we will use the default success and
         * failure handlers.
         */
        config: {
            value: null
        }
    };

    /* Extend the DomUpdater plugin class */
    Y.extend(LP.DynamicDomUpdater, DomUpdater, {

        initializer: function(config){
            Y.log("Initializing", "info", "LPDynamicDomUpdater");

            // Create the configuration for the LP client request.
            this.set("config", {
                on: {
                    success: Y.bind(this._handleSuccess, this),
                    failure: Y.bind(this._handleFailure, this)
                }
            });
            // Create our own instance of the LP client.
            this.client = new LP.client.Launchpad();

            // Finally, setup our timeout interval to update ourselves.
            setInterval(
                Y.bind(this.dynamicUpdate, this),
                this.get('interval')
                );
        },

        /*
         * update the DOM subtree with data from a dynamic source.
         */
        dynamicUpdate: function() {
            Y.log("Updating", "info", "LP.DynamicDomUpdater");
            uri = this.get("uri");
            api_method_name = this.get("api_method_name");
            config = this.get("config");
            if (uri){
                if (api_method_name){
                    this.client.named_get(uri, api_method_name, config);
                }
                else {
                    this.client.get(uri, config);
                }
            }
        },

        /*
         * Handlers for success and failure of LP Client request.
         * These will be used if a configuration for the request is not
         * provided.
         */
        _handleSuccess: function(data, something) {
            Y.log("Data received", "info", "LP.DynamicDomUpdater");
            // Call our parent classes update method to update the DOM
            // subtree with the returned data.
            this.update(data);
        },

        _handleFailure: function(id, request) {
            Y.log("Failed to get dynamic data", "info",
                  "LP.DynamicDomUpdater");
        }
    });
});

