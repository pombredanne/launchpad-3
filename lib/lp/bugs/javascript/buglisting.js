/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Client-side rendering of bug listings.
 *
 * @module bugs
 * @submodule buglisting
 */

YUI.add('lp.bugs.buglisting', function(Y) {

var module = Y.namespace('lp.bugs.buglisting');


/**
 * Constructor.
 *
 * This is the model of the current batch, including the ordering, position,
 * and what fields are visibile.
 *
 * These values are stored in the History object, so that the browser
 * back/next buttons correctly adjust.  The system defaults for field
 * visibility are fixed, so they are stored directly on the object.
 *
 * Accepts a config containing:
 *  - field_visibility the requested field visibility as an associative array
 *  - field_visibility_defaults the system defaults for field visibility as an
 *    associative array.
 *  - batch_key: A string representing the position and ordering of the
 *    current batch, as returned by listing_navigator.get_batch_key
 */
module.BugListingModel = function() {
    module.BugListingModel.superclass.constructor.apply(this, arguments);
};


module.BugListingModel.NAME = 'buglisting-model';


module.BugListingModel.ATTRS = {
    field_visibility_defaults: {
        value: null
    }
};


Y.extend(module.BugListingModel, Y.Base, {
    /**
     * Initializer sets up the History object that stores most of the model
     * data.
     */
    initializer: function(config) {
        this.set('history', new Y.History({
            initialState: Y.merge(
                config.field_visibility, {batch_key: config.batch_key})
        }));
    },

    /**
     * Return the current field visibility, as an associative array.
     * Since the history contains field values that are not field-visibility,
     * use field_visibility_defaults to filter out non-field-visibility
     * values.
     */
    get_field_visibility: function() {
        var result = this.get('history').get();
        var key_source = this.get('field_visibility_defaults');
        Y.each(result, function(value, key) {
            if (!key_source.hasOwnProperty(key)){
                delete result[key];
            }
        });
        return result;
    },

    /**
     * Set the field visibility, updating history.  Accepts an associative
     * array.
     */
    set_field_visibility: function(value) {
        this.get('history').add(value);
    },

    /**
     * Return the current batch key.
     */
    get_batch_key: function() {
        return this.get('history').get('batch_key');
    },

    /**
     * Set the current batch.  The batch_key and the query mapping identifying
     * the batch must be supplied.
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
 * navigation_indices is a YUI NodeList of nodes to update with the current
 * batch info.
 * io_provider is something providing the Y.io interface, typically used for
 * testing.  Defaults to Y.io.
 */
module.BugListingNavigator = function(config) {
    module.BugListingNavigator.superclass.constructor.apply(
        this, arguments);
};

module.BugListingNavigator.ATTRS = {
};

Y.extend(
    module.BugListingNavigator,
    Y.lp.app.listing_navigator.ListingNavigator, {
    initializer: function(config) {
        this.constructor.superclass.initializer.apply(this, arguments);
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
            this.pre_fetch_batches();
            this.render();
        }
        else {
            // Handle Chrom(e|ium)'s initial popstate.
            this.get('model').get('history').replace(e.prevVal);
        }
    },

    /**
     * Return the model to use for rendering the batch.  This will include
     * updates to field visibility.
     */
    get_render_model: function(current_batch) {
        return Y.merge(
            current_batch.mustache_model,
            this.get('model').get_field_visibility());
    },

    /**
     * Handle a previously-unseen batch by storing it in the cache and
     * stripping out field_visibility values that would otherwise shadow the
     * real values.
     */
    handle_new_batch: function(batch) {
        var key, i;
        Y.each(batch.field_visibility, function(value, key) {
            for (i = 0; i < batch.mustache_model.items.length; i++) {
                delete batch.mustache_model.items[i][key];
            }
        });
        return this.constructor.superclass.handle_new_batch.call(this, batch);
    }

},{
    make_model: function(batch_key, cache) {
        return new module.BugListingModel({
                batch_key: batch_key,
                field_visibility: cache.field_visibility,
                field_visibility_defaults: cache.field_visibility_defaults
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

/**
 * Factory to return a BugListingNavigator for the given page.
 */
module.BugListingNavigator.from_page = function() {
    var target = Y.one('#client-listing');
    if (Y.Lang.isNull(target)){
        return null;
    }
    var navigation_indices = Y.all('.batch-navigation-index');
    var pre_fetch = Y.lp.app.listing_navigator.get_feature_flag(
        'bugs.dynamic_bug_listings.pre_fetch');
    Y.lp.app.listing_navigator.linkify_navigation();
    var navigator = new module.BugListingNavigator({
        current_url: window.location,
        cache: LP.cache,
        template: LP.mustache_listings,
        target: target,
        navigation_indices: navigation_indices,
        pre_fetch: Boolean(pre_fetch)
    });
    navigator.set('backwards_navigation', Y.all('.first,.previous'));
    navigator.set('forwards_navigation', Y.all('.last,.next'));
    navigator.clickAction('.first', navigator.first_batch);
    navigator.clickAction('.next', navigator.next_batch);
    navigator.clickAction('.previous', navigator.prev_batch);
    navigator.clickAction('.last', navigator.last_batch);
    navigator.render_navigation();
    return navigator;
};



}, "0.1", {
    "requires": [
        "history", "node", 'lp.app.listing_navigator']
});
