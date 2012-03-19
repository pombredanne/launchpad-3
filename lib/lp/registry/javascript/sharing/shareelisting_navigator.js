/* Copyright 2012 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Batch navigation support for sharees.
 *
 * @module registry
 * @submodule sharing
 */

YUI.add('lp.registry.sharing.shareelisting_navigator', function (Y) {

    var module = Y.namespace('lp.registry.sharing.shareelisting_navigator');


    /**
     * Constructor.
     *
     * This is the model of the current batch.
     *
     * These values are stored in the History object, so that the browser
     * back/next buttons correctly adjust.
     *
     * Accepts a config containing:
     *  - batch_key: A string representing the position and ordering of the
     *    current batch, as returned by listing_navigator.get_batch_key
     */
    module.ShareeListingModel = function () {
        module.ShareeListingModel.superclass.constructor.apply(this, arguments);
    };


    module.ShareeListingModel.NAME = 'shareelisting-model';

    module.ShareeListingModel.ATTRS = {
    };


    Y.extend(module.ShareeListingModel, Y.Base, {
        /**
         * Initializer sets up the History object that stores most of the
         * model data.
         */
        initializer: function(config) {
            this.set('history', new Y.History({
                initialState: {
                        batch_key: config.batch_key
                    }
            }));
        },

        /**
         * Return the current batch key.
         */
        get_batch_key: function() {
            return this.get('history').get('batch_key');
        },

        /**
         * Set the current batch.  The batch_key and the query mapping
         * identifying the batch must be supplied.
         */
        set_batch: function(batch_key, query) {
            var url = '?' + Y.QueryString.stringify(query);
            this.get('history').addValue('batch_key', batch_key, {url: url});
        }
    });


    /**
     * Constructor.
     * current_url is used to determine search params.
     * cache is the JSONRequestCache for the batch.
     * template is the template to use for rendering batches.
     * target is a YUI node to update when rendering batches.
     * navigation_indices is a YUI NodeList of nodes to update with the
     * current batch info.
     * io_provider is something providing the Y.io interface, typically used
     * for testing.  Defaults to Y.io.
     */
    module.ShareeListingNavigator = function(config) {
        module.ShareeListingNavigator.superclass.constructor.apply(
            this, arguments);
    };

    module.ShareeListingNavigator.ATTRS = {
        sharee_table_widget: {
            value: null
        }
    };

    Y.extend(
        module.ShareeListingNavigator,
        Y.lp.app.listing_navigator.ListingNavigator, {

        initializer: function(config) {
            this.get('model').get('history').after(
                'change', this.history_changed, this);
        },
        /**
         * Event handler for history:change events.
         */
        history_changed: function(e) {
            if (e.newVal.hasOwnProperty('batch_key')) {
                var batch_key = e.newVal.batch_key;
                var batch = this.get('batches')[batch_key];
//                this.pre_fetch_batches();
                this.render();
                this.syncUI();
                this._bindUI();
            }
            else {
                // Handle Chrom(e|ium)'s initial popstate.
                this.get('model').get('history').replace(e.prevVal);
            }
        },

    render: function() {
        var current_batch = this.get_current_batch();
        var batch_info = Y.lp.mustache.to_html(this.get('batch_info_template'), {
            start: current_batch.start + 1,
            end: current_batch.start +
                current_batch.sharee_data.length,
            total: current_batch.total
        });
        this.get('navigation_indices').setContent(batch_info);
        this.render_navigation();
    },

       syncUI: function() {
           var current_batch = this.get_current_batch();
           LP.cache.sharee_data = current_batch.sharee_data;
           this.get('sharee_table_widget').syncUI();
       },

        _bindUI: function () {
            Y.lp.app.inlinehelp.init_help();
        }
    },{
        make_model: function(batch_key, cache) {
            return new module.ShareeListingModel({
                    batch_key: batch_key
            });
        },
        get_search_params: function(config) {
            var search_params = Y.lp.app.listing_navigator.get_query(
                config.current_url);
            delete search_params.start;
            delete search_params.memo;
            delete search_params.direction;
            delete search_params.orderby;
            return search_params;
        }
    });

}, '0.1', {
    'requires': [
        'history', 'node', 'lp.app.listing_navigator', 'lp.app.inlinehelp',
        'lp.app.indicator', 'lp.ordering'
    ]
});
