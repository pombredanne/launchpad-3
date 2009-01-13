/** Copyright (c) 2008, Canonical Ltd. All rights reserved. 
 *
 * The Launchpad DynamicDomUpdater module provides a plugin class that
 * can be plugged in to a DOM subtree, so that the subtree can update itself
 * regularly using the Launchpad API.
 *
 * @module DynamicDomUpdater
 * @requires yahoo, node, plugin, LP
 */

LP = (typeof(LP) != "undefined") ? LP : {};
LP.DynamicDomUpdater = (typeof LP.DynamicDomUpdater != "undefined") ? LP.DynamicDomUpdater : null;

YUI().use("node", "plugin", function(Y) {

    /**
     * The DomUpdater class provides the ability to plugin functionality 
     * to a DOM subtree so that it can update itself when given data in an
     * expected format.
     *
     * For example:
     *     var table = Y.get('table#build-count-table');
     *     var config = {
     *         owner: table,
     *         domUpdateFunction: updateArchiveBuildStatusSummary
     *     }
     *     table.plug(LP.DomUpdater, config);
     *
     *     // Now updating the table is as simple as:
     *     table.updater.update({total:3, failed: 1});
     *
     * @class DomUpdater
     * @extends Plugin
     * @constructor
     */
    var DomUpdater = function(config){
        DomUpdater.superclass.constructor.apply(this, arguments);
    };

    DomUpdater.NAME = 'domupdater';
    DomUpdater.NS = 'updater';

    DomUpdater.ATTRS = {
        /**
         * The dom node to which this plugin instance is attached.
         * @attribute owner
         * @type Node
         */
        owner: {
            value: null
        },

        /**
         * The function that updates the owner's dom subtree.
         * @attribute domUpdateFunction
         * @type Function
         * @default null
         */
        domUpdateFunction: {
            value: null
        }
    };

    /* 
     * Extend from Y.Plugin.
     */
    Y.extend(DomUpdater, Y.Plugin, {

        /**
         * 
         */
        update: function(update_data) {
            Y.log("Updating Dom subtree for " + this.get("owner"),
                  "info", "DomUpdater");
            var domUpdateFunction = this.get("domUpdateFunction");
            if (domUpdateFunction !== null){
                domUpdateFunction(this.get("owner"), update_data);
            }
        }

    });

    /**
     * This class provides the ability to plugin functionality to a DOM
     * subtree so that it can update itself using an LP api method.
     *
     * For example:
     *     var table = Y.get('table#build-count-table');
     *     var config = {
     *         owner: table,
     *         domUpdateFunction: updateArchiveBuildStatusSummary,
     *         uri: LP.client.cache.context.self_link,
     *         api_method_name: 'getBuildCounters'
     *     }
     *     table.plug(LP.DynamicDomUpdater, config);
     *
     * Once configured, the 'table' dom subtree will now update itself
     * (with a default interval of 6000ms) with the result of the LP
     * api call.
     * 
     * @class DynamicDomUpdater
     * @extends DomUpdater
     * @constructor
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
         * The LP client to use. If none is provided, one will be
         * created during initialization.
         */
        lp_client: {
            value: null
        },

        /*
         * The LP api method name (if applicable).
         */
        api_method_name: {
            value: null
        },

        /*
         * The function that provides the parameters for the API call.
         *
         * If this is not specified, no parameters will be included.
         */
        parameter_evaluator_function: {
            value: null
        },

        /*
         * The default refresh interval in ms.
         */
        interval: {
            value: 60000
        },

        /*
         * The function used to determine whether updates should stop.
         *
         * If it is not included, we use a default function that always
         * returns false so the updates will continue infinitely.
         *
         * Once this function returns true, updates will stop and not
         * be restarted.
         */
        stop_updates_check: {
            value: function(data){return false;}
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
            Y.log("Initializing updater for " + this.get("owner"),
                  "info", "LPDynamicDomUpdater");

            // Create the configuration for the LP client request, and
            // copy the parameters from our attributes.
            if (null === this.get("config")){
                this.set("config", {
                    on: {
                        success: Y.bind(this._handleSuccess, this),
                        failure: Y.bind(this._handleFailure, this)
                    }
                });
            }

            if (null === this.get("lp_client")){
                // Create our own instance of the LP client.
                this.set("lp_client", new LP.client.Launchpad());
            }

            // Finally, setup our timeout interval to update ourselves.
            this.intervalID = setInterval(
                Y.bind(this.dynamicUpdate, this),
                this.get('interval')
                );
        },

        /*
         * update the DOM subtree with data from a dynamic source.
         */
        dynamicUpdate: function() {
            Y.log("Starting update for " + this.get("owner"),
                  "info", "LP.DynamicDomUpdater");
            var uri = this.get("uri");
            var api_method_name = this.get("api_method_name");
            var config = this.get("config");

            // Check whether we should stop updating now...
            if (this.get("stop_updates_check")(this.get("owner"))){
                Y.log(
                    "Cancelling updates for " + this.get("owner") +
                    "after stop_updates_check returned true.", "info",
                    "LP DynamicDomUpdater");
                clearInterval(this.intervalID);
                return;
            }

            // Set any parameters for the API call:
            var parameter_evaluator_function = this.get(
                "parameter_evaluator_function");
            if (parameter_evaluator_function !== null){
                config.parameters = parameter_evaluator_function(
                    this.get("owner"));
            }

            if (uri){
                if (api_method_name){
                    this.get("lp_client").named_get(uri,
                        api_method_name, config);
                }
                else {
                    this.get("lp_client").get(uri, config);
                }
            }
        },

        /*
         * Handlers for success and failure of LP Client request.
         * These will be used if a configuration for the request is not
         * provided.
         */
        _handleSuccess: function(data, something) {
            Y.log("Data received for " + this.get("owner"),
                   "info", "LP.DynamicDomUpdater");
            // Call our parent class's update method to update the DOM
            // subtree with the returned data.
            this.update(data);
        },

        _handleFailure: function(id, request) {
            Y.fail("LP.DynamicDomUpdater for " + this.get("owner") +
                   "failed to get dynamic data.");
        }
    });
});

