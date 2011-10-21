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
 * Render bug listings via Mustache.
 *
 * If model is supplied, it is used as the data for rendering the listings.
 * Otherwise, LP.cache.mustache_model is used.
 *
 * The template is always LP.mustache_listings.
 */
namespace.rendertable = function(model){
    client_listing = Y.one('#client-listing');
    if (client_listing === null){
        return;
    }
    if (!Y.Lang.isValue(model)){
        model = LP.cache.mustache_model;
    }
    var txt = Mustache.to_html(LP.mustache_listings, model);
    client_listing.set('innerHTML', txt);
};

/**
 * A shim to use the data of an LP.cache to render the bug listings and cache
 * their data.
 *
 * order_by is the ordering used by the model.
 */
namespace.update_from_model = function(order_by, model){
    namespace.batches[order_by] = model.mustache_model;
    namespace.rendertable(model.mustache_model);
};


namespace.get_batch_query = function(current_url, config){
    var query = namespace.get_query(current_url);
    if (Y.Lang.isValue(config.order_by)){
        query.orderby = config.order_by;
    }
    if (Y.Lang.isValue(config.memo)){
        query.memo = config.memo;
    }
    if (Y.Lang.isValue(config.forward)){
        if (config.forward){
            delete query.direction;
        }
        else {
            query.direction = 'reverse';
        }
    }
    return query;
};


/**
 * Update the bug listings.
 *
 * order_by is a string specifying the sort order, as it would appear in a
 * URL.
 *
 * Config may contain an io_provider.
 */
namespace.update_listing = function(order_by, config){
    var lp_client, cache, query;
    if (Y.Lang.isValue(namespace.batches[order_by])){
        namespace.update_from_model(order_by, namespace.batches[order_by]);
        return;
    }
    lp_client = new Y.lp.client.Launchpad();
    cache = lp_client.wrap_resource(null, LP.cache);
    query = namespace.get_batch_query(window.location, {order_by: order_by});
    load_model_config = {
        on: {
            success: Y.bind(namespace.update_from_model, window, order_by)
        }
    };
    if (Y.Lang.isValue(config)){
        load_model_config.io_provider = config.io_provider;
    }
    Y.lp.client.load_model(
        cache.context, '+bugs', load_model_config, query);
};


/**
 * Return the query of the specified URL in structured form.
 */
namespace.get_query = function(url){
    var querystring = Y.lp.get_url_query(url);
    return Y.QueryString.parse(querystring);
};


namespace.batches = {};

}, "0.1", {"requires": ["node", 'lp.client']});
