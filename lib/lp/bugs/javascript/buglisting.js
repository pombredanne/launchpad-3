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


namespace.ListingNavigator = function(current_url, cache, template, target,
                                      io_provider) {
    var lp_client = new Y.lp.client.Launchpad();
    this.current_url = current_url;
    this.io_provider = io_provider;
    this.view_model = lp_client.wrap_resource(null, cache);
    this.template = template;
    this.target = target;
    this.batches = {};
};


namespace.ListingNavigator.fromPage = function(){
    var target = Y.one('#client-listing');
    var navigator = new namespace.ListingNavigator(
        window.location, LP.cache, LP.mustache_listings, target);
    var last = Y.all('.last');
    var first = Y.all('.first');
    last.on('click', function(e){
        e.preventDefault();
        navigator.last_batch();
    });
    last.addClass('js-action');
    first.on('click', function(e){
        e.preventDefault();
        navigator.first_batch();
    });
    first.removeClass('inactive');
    first.addClass('js-action');
    return navigator;
};


/**
 * Render bug listings via Mustache.
 *
 * If model is supplied, it is used as the data for rendering the listings.
 * Otherwise, LP.cache.mustache_model is used.
 *
 * The template is always LP.mustache_listings.
 */
namespace.ListingNavigator.prototype.rendertable = function(model){
    if (! Y.Lang.isValue(this.target)){
        return;
    }
    if (!Y.Lang.isValue(model)){
        model = this.view_model.mustache_model;
    }
    var txt = Mustache.to_html(this.template, model);
    this.target.set('innerHTML', txt);
};


/**
 * A shim to use the data of an LP.cache to render the bug listings and cache
 * their data.
 *
 * order_by is the ordering used by the model.
 */
namespace.ListingNavigator.prototype.update_from_model = function(order_by,
                                                                  model){
    this.batches[order_by] = model.mustache_model;
    this.rendertable(model.mustache_model);
};


namespace.ListingNavigator.prototype.get_batch_query = function(config){
    var query = namespace.get_query(this.current_url);
    if (Y.Lang.isValue(config.order_by)){
        query.orderby = config.order_by;
    }
    if (Y.Lang.isValue(config.memo)){
        query.memo = config.memo;
    }
    else if (config.memo === null){
        delete query.memo;
    }
    if (Y.Lang.isValue(config.forward)){
        if (config.forward){
            delete query.direction;
        }
        else {
            query.direction = 'backwards';
        }
    }
    return query;
};


/**
 * Update the bug listings.
 *
 * order_by is a string specifying the sort order, as it would appear in a
 * URL.
 */
namespace.ListingNavigator.prototype.change_ordering = function(order_by){
    var query;
    if (Y.Lang.isValue(this.batches[order_by])){
        this.update_from_model(order_by, this.batches[order_by]);
        return;
    }
    this.load_model({order_by: order_by});
};

namespace.ListingNavigator.prototype.last_batch = function(order_by){
    this.load_model({forward: false, memo: null});
};


namespace.ListingNavigator.prototype.first_batch = function(order_by){
    this.load_model({forward: true, memo: null});
};


namespace.ListingNavigator.prototype.load_model = function(config){
    var query = this.get_batch_query(config);
    var load_model_config = {
        on: {
            success: Y.bind(this.update_from_model, this, config.order_by)
        }
    };
    if (Y.Lang.isValue(this.io_provider)){
        load_model_config.io_provider = this.io_provider;
    }
    Y.lp.client.load_model(
        this.view_model.context, '+bugs', load_model_config, query);
};


/**
 * Return the query of the specified URL in structured form.
 */
namespace.get_query = function(url){
    var querystring = Y.lp.get_url_query(url);
    return Y.QueryString.parse(querystring);
};


}, "0.1", {"requires": ["node", 'lp.client']});
