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


function empty_nodelist() {
    return new Y.NodeList([]);
}


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
namespace.ListingNavigator = function(config) {
    namespace.ListingNavigator.superclass.constructor.apply(this, arguments);
};


namespace.ListingNavigator.ATTRS = {
    batches: {value: {}},
    batch_info_template: {value: '<strong>{{start}}</strong> &rarr; ' +
        '<strong>{{end}}</strong> of {{total}} results'},
    backwards_navigation: {valueFn: empty_nodelist},
    forwards_navigation: {valueFn: empty_nodelist},
    io_provider: {value: null},
    pre_fetch: {value: false},
    navigation_indices: {valueFn: empty_nodelist},
    spinners: {valueFn: empty_nodelist}
};

Y.extend(namespace.ListingNavigator, Y.Base, {
    initializer: function(config) {
        var lp_client = new Y.lp.client.Launchpad();
        var cache = lp_client.wrap_resource(null, config.cache);
        var batch_key;
        var template = config.template;
        this.set('search_params', namespace.get_query(config.current_url));
        delete this.get('search_params').start;
        delete this.get('search_params').memo;
        delete this.get('search_params').direction;
        delete this.get('search_params').orderby;
        this.set('io_provider', config.io_provider);
        batch_key = this.handle_new_batch(cache);
        this.set('model', new namespace.BugListingModel({
                batch_key: batch_key,
                field_visibility: cache.field_visibility,
                field_visibility_defaults: cache.field_visibility_defaults
        }));
        this.pre_fetch_batches();
        // Work around mustache.js bug 48 "Blank lines are not preserved."
        // https://github.com/janl/mustache.js/issues/48
        if (Y.Lang.isValue(template)) {
            template = template.replace(/\n/g, '&#10;');
        }
        this.set('template', template);
        this.set_pending(false);
        this.set('target', config.target);
        if (Y.Lang.isValue(config.navigation_indices)) {
            this.set('navigation_indices', config.navigation_indices);
        }
        this.get('model').get('history').after(
            'change', this.history_changed, this);
    },

    get_failure_handler: function(fetch_only){
        var error_handler = new Y.lp.client.ErrorHandler();
        error_handler.showError = Y.bind(
            Y.lp.app.errors.display_error, window, null);
        if (!fetch_only){
            error_handler.clearProgressUI = Y.bind(
                this.set_pending, this, false);
        }
        return error_handler.getFailureHandler();
    },

    /**
     * Event handler for history:change events.
     */
    history_changed: function(e){
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
     * Call the callback when a node matching the selector is clicked.
     *
     * The node is also marked up appropriately.
     */
    clickAction: function(selector, callback) {
        var nodes = Y.all(selector);
        nodes.on('click', function(e) {
            e.preventDefault();
            callback.call(this);
        }, this);
        nodes.addClass('js-action');
    },

    /**
     * Retrieve the current batch for rendering purposes.
     */
    get_current_batch: function(){
        var batch_key = this.get('model').get('history').get('batch_key');
        return this.get('batches')[batch_key];
    },

    /**
     * Handle a previously-unseen batch by storing it in the cache and
     * stripping out field_visibility values that would otherwise shadow the
     * real values.
     */
     handle_new_batch: function(batch) {
        var key, i;
        var batch_key = this.constructor.get_batch_key(batch);
        Y.each(batch.field_visibility, function(value, key) {
            for (i = 0; i < batch.mustache_model.bugtasks.length; i++) {
                delete batch.mustache_model.bugtasks[i][key];
            }
        });
        this.get('batches')[batch_key] = batch;
        return batch_key;
    },

    /**
     * Render bug listings via Mustache.
     *
     * If model is supplied, it is used as the data for rendering the
     * listings.  Otherwise, LP.cache.mustache_model is used.
     *
     * The template is always LP.mustache_listings.
     */
    render: function() {
        var current_batch = this.get_current_batch();
        var model = Y.merge(
            current_batch.mustache_model,
            this.get('model').get_field_visibility());
        var batch_info = Mustache.to_html(this.get('batch_info_template'), {
            start: current_batch.start + 1,
            end: current_batch.start +
                current_batch.mustache_model.bugtasks.length,
            total: current_batch.total
        });
        var content = Mustache.to_html(this.get('template'), model);
        this.get('target').setContent(content);
        this.get('navigation_indices').setContent(batch_info);
        this.render_navigation();
    },

    set_pending: function(is_pending){
        if (is_pending){
            this.get('spinners').setStyle('visibility', 'visible');
        }
        else{
            this.get('spinners').setStyle('visibility', 'hidden');
        }
    },

    has_prev: function(){
        return !Y.Lang.isNull(this.get_current_batch().prev);
    },

    has_next: function(){
        return !Y.Lang.isNull(this.get_current_batch().next);
    },

    /**
     * Enable/disable navigation links as appropriate.
     */
    render_navigation: function() {
        this.get('backwards_navigation').toggleClass(
            'inactive', !this.has_prev());
        this.get('forwards_navigation').toggleClass(
            'inactive', !this.has_next());
    },

    update_from_new_model: function(query, fetch_only, model){
        var batch_key = this.handle_new_batch(model);
        if (fetch_only) {
            return;
        }
        this.set_pending(false);
        this.update_from_cache(query, batch_key);
    },

    /**
     * A shim to use the data of an LP.cache to render the bug listings and
     * cache their data.
     *
     * query is a mapping of query variables generated by get_batch_query.
     * batch_key is the key generated by get_batch_key for the model.
     */
    update_from_cache: function(query, batch_key) {
        var url = '?' + Y.QueryString.stringify(query);
        this.get('model').get('history').addValue(
            'batch_key', batch_key, {url: url});
    },

    /**
     * Return the query vars to use for the specified batch.
     * This includes the search params and the batch selector.
     */
    get_batch_query: function(config) {
        var query = Y.merge(
            this.get('search_params'), {orderby: config.order_by});
        if (Y.Lang.isValue(config.memo)) {
            query.memo = config.memo;
        }
        if (Y.Lang.isValue(config.start)) {
            query.start = config.start;
        }
        if (config.forwards !== undefined && !config.forwards) {
            query.direction = 'backwards';
        }
        return query;
    },


    /**
     * Pre-fetch adjacent batches.
     */
    pre_fetch_batches: function(){
        var that=this;
        if (!this.get('pre_fetch')){
            return;
        }
        Y.each(this.get_pre_fetch_configs(), function(config){
            config.fetch_only = true;
            that.update(config);
        });
    },


    /**
     * Update the display to the specified batch.
     *
     * If the batch is cached, it will be used immediately.  Otherwise, it
     * will be retrieved and cached upon retrieval.
     */
    update: function(config) {
        var key = this.constructor.get_batch_key(config);
        var cached_batch = this.get('batches')[key];
        var query = this.get_batch_query(config);
        if (Y.Lang.isValue(cached_batch)) {
            if (config.fetch_only){
                return;
            }
            this.update_from_cache(query, key);
        }
        else {
            this.load_model(query, config.fetch_only);
        }
    },

    /**
     * Update the navigator to display the last batch.
     */
    last_batch: function() {
        var current_batch = this.get_current_batch();
        this.update({
            forwards: false,
            memo: "",
            start: current_batch.last_start,
            order_by: current_batch.order_by
        });
    },

    first_batch_config: function(order_by){
        if (order_by === undefined) {
            order_by = this.get_current_batch().order_by;
        }
        return {
            forwards: true,
            memo: null,
            start: 0,
            order_by: order_by
        };
    },

    /**
     * Update the navigator to display the first batch.
     *
     * The order_by defaults to the current ordering, but may be overridden.
     */
    first_batch: function(order_by) {
        this.update(this.first_batch_config(order_by));
    },

    next_batch_config: function(){
        var current_batch = this.get_current_batch();
        if (!this.has_next()){
            return null;
        }
        return {
            forwards: true,
            memo: current_batch.next.memo,
            start: current_batch.next.start,
            order_by: current_batch.order_by
        };
    },
    /**
     * Update the navigator to display the next batch.
     */
    next_batch: function() {
        var config = this.next_batch_config();
        if (config === null){
            return;
        }
        this.update(config);
    },
    prev_batch_config: function(){
        var current_batch = this.get_current_batch();
        if (!this.has_prev()){
            return null;
        }
        return {
            forwards: false,
            memo: current_batch.prev.memo,
            start: current_batch.prev.start,
            order_by: current_batch.order_by
        };
    },
    /**
     * Update the navigator to display the previous batch.
     */
    prev_batch: function() {
        var config = this.prev_batch_config();
        if (config === null){
            return;
        }
        this.update(config);
    },
    /**
     * Generate a list of configs to pre-fetch.
     */
    get_pre_fetch_configs: function(){
        var configs = [];
        var next_batch_config = this.next_batch_config();
        if (next_batch_config !== null){
            configs.push(next_batch_config);
        }
        return configs;
    },

    /**
     * Load the specified batch via ajax.  Display & cache on load.
     *
     * query is the query string for the URL, as a mapping.  (See
     * get_batch_query).
     */
    load_model: function(query, fetch_only) {
        var load_model_config = {
            on: {
                success: Y.bind(
                    this.update_from_new_model, this, query, fetch_only),
                failure: this.get_failure_handler(fetch_only)
            }
        };
        var context = this.get_current_batch().context;
        if (Y.Lang.isValue(this.get('io_provider'))) {
            load_model_config.io_provider = this.get('io_provider');
        }
        if (!fetch_only){
            this.set_pending(true);
        }
        Y.lp.client.load_model(
            context, '+bugs', load_model_config, query);
    }
});


/**
 * Rewrite all nodes with navigation classes so that they are hyperlinks.
 * Content is retained.
 */
namespace.linkify_navigation = function() {
    Y.each(['previous', 'next', 'first', 'last'], function(class_name) {
        Y.all('.' + class_name).each(function(node) {
            new_node = Y.Node.create('<a href="#"></a>');
            new_node.addClass(class_name);
            new_node.setContent(node.getContent());
            node.replace(new_node);
            if (class_name === 'first'){
                var spinner_node = Y.Node.create(
                    '<img class="spinner" src="/@@/spinner"'+
                    ' alt="Loading..." />');
                new_node.insertBefore(spinner_node, new_node);
            }
        });
    });
};


/**
 * Return the value for a given feature flag in the current scope.
 * Only flags declared as "related_features" on the view are available.
 */
var get_feature_flag = function(flag_name){
    return LP.cache.related_features[flag_name].value;
};


/**
 * Factory to return a ListingNavigator for the given page.
 */
namespace.ListingNavigator.from_page = function() {
    var target = Y.one('#client-listing');
    var navigation_indices = Y.all('.batch-navigation-index');
    var pre_fetch = get_feature_flag('bugs.dynamic_bug_listings.pre_fetch');
    namespace.linkify_navigation();
    var navigator = new namespace.ListingNavigator({
        current_url: window.location,
        cache: LP.cache,
        template: LP.mustache_listings,
        target: target,
        navigation_indices: navigation_indices,
        pre_fetch: Boolean(pre_fetch),
        spinners: Y.all('.spinner')
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


/**
 * Get the key for the specified batch, for use in the batches mapping.
 */
namespace.ListingNavigator.get_batch_key = function(config) {
    return JSON.stringify([config.order_by, config.memo, config.forwards,
                           config.start]);
};


/**
 * Return the query of the specified URL in structured form.
 */
namespace.get_query = function(url) {
    var querystring = Y.lp.get_url_query(url);
    return Y.QueryString.parse(querystring);
};


}, "0.1", {"requires": ["history", "node", 'lp.client', 'lp.app.errors']});
