/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 *
 * Client-side rendering of bug listings.
 *
 * @module bugs
 * @submodule buglisting
 */

YUI.add('lp.bugs.buglisting', function(Y) {

var namespace = Y.namespace('lp.bugs.buglisting');


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
 *    current batch, as returned by ListingNavigator.get_batch_key
 */
namespace.BugListingModel = function(){
    namespace.BugListingModel.superclass.constructor.apply(this, arguments);
};


namespace.BugListingModel.NAME = 'buglisting-model';


namespace.BugListingModel.ATTRS = {
    field_visibility_defaults: {
        value: null
    }
};


Y.extend(namespace.BugListingModel, Y.Base, {
    /**
     * Initializer sets up the History object that stores most of the model
     * data.
     */
    initializer: function(config){
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
    get_field_visibility: function(){
        var result = this.get('history').get();
        var key_source = this.get('field_visibility_defaults');
        Y.each(result, function(value, key){
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
    set_field_visibility: function(value){
        this.get('history').add(value);
    }
});


namespace.BugListingNavigator = function(config) {
    namespace.BugListingNavigator.superclass.constructor.apply(
        this, arguments);
};

namespace.BugListingNavigator.ATTRS = {
};

Y.extend(
    namespace.BugListingNavigator,
    Y.lp.app.listing_navigator.ListingNavigator, {},
    {
    make_model: function(batch_key, cache) {
        return new namespace.BugListingModel({
                batch_key: batch_key,
                field_visibility: cache.field_visibility,
                field_visibility_defaults: cache.field_visibility_defaults
        });
    },
    get_search_params: function(config){
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
 * Factory to return a ListingNavigator for the given page.
 */
namespace.BugListingNavigator.from_page = function() {
    var target = Y.one('#client-listing');
    if (Y.Lang.isNull(target)){
        return null;
    }
    var navigation_indices = Y.all('.batch-navigation-index');
    var pre_fetch = Y.lp.app.listing_navigator.get_feature_flag(
        'bugs.dynamic_bug_listings.pre_fetch');
    Y.lp.app.listing_navigator.linkify_navigation();
    var navigator = new namespace.BugListingNavigator({
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
        "history", "node", 'lp.client', 'lp.app.errors',
        'lp.app.listing_navigator', 'lp.indicator'
    ]
});
