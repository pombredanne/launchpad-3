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
    io_provider: {value: null}
};


Y.extend(namespace.ListingNavigator, Y.Base, {
    initializer: function(config){
        var lp_client = new Y.lp.client.Launchpad();
        var cache = lp_client.wrap_resource(null, config.cache);
        var template = config.template;
        this.set('search_params', namespace.get_query(config.current_url));
        delete this.get('search_params').start;
        delete this.get('search_params').memo;
        delete this.get('search_params').direction;
        delete this.get('search_params').orderby;
        this.set('io_provider', config.io_provider);
        this.set('field_visibility', cache.field_visibility);
        this.handle_new_batch(cache);
        this.set('current_batch', cache);
        //Work around mustache.js bug 48 "Blank lines are not preserved."
        // https://github.com/janl/mustache.js/issues/48
        if (Y.Lang.isValue(template)){
            template = template.replace(/\n/g, '&#10;');
        }
        this.set('template', template);
        this.target = config.target;
        this.backwards_navigation = new Y.NodeList([]);
        this.forwards_navigation = new Y.NodeList([]);
        this.navigation_indices = config.navigation_indices;
        if (!Y.Lang.isValue(this.navigation_indices)){
            this.navigation_indices = new Y.NodeList([]);
        }
        this.batch_info_template = '<strong>{{start}}</strong> &rarr; ' +
            '<strong>{{end}}</strong> of {{total}} results';
    },
    /**
     * Call the callback when a node matching the selector is clicked.
     *
     * The node is also marked up appropriately.
     */
    clickAction: function(selector, callback){
        that = this;
        var nodes = Y.all(selector);
        nodes.on('click', function(e){
            e.preventDefault();
            callback.call(that);
        });
        nodes.addClass('js-action');
    },

    /**
     * Handle a previously-unseen batch by storing it in the cache and
     * stripping out field_visibility values that would otherwise shadow the
     * real values.
     */
     handle_new_batch: function(batch){
        var key, i;
        var batch_key = namespace.ListingNavigator.get_batch_key(batch);
        Y.each(this.get('field_visibility'), function(value, key){
            for (i = 0; i < batch.mustache_model.bugtasks.length; i++){
                delete batch.mustache_model.bugtasks[i][key];
            }
        });
        this.get('batches')[batch_key] = batch;
    },

    /**
     * Render bug listings via Mustache.
     *
     * If model is supplied, it is used as the data for rendering the
     * listings.  Otherwise, LP.cache.mustache_model is used.
     *
     * The template is always LP.mustache_listings.
     */
    render: function(){
        var model = Y.merge(
            this.get('current_batch').mustache_model,
            this.get('field_visibility'));
        var batch_info = Mustache.to_html(this.batch_info_template, {
            start: this.get('current_batch').start + 1,
            end: this.get('current_batch').start +
                this.get('current_batch').mustache_model.bugtasks.length,
            total: this.get('current_batch').total
        });
        this.target.setContent(Mustache.to_html(this.get('template'), model));
        this.navigation_indices.setContent(batch_info);
        this.render_navigation();
    },

    /**
     * Enable/disable navigation links as appropriate.
     */
    render_navigation: function(){
        this.backwards_navigation.toggleClass(
            'inactive', this.get('current_batch').prev === null);
        this.forwards_navigation.toggleClass(
            'inactive', this.get('current_batch').next === null);
    },

    /**
     * A shim to use the data of an LP.cache to render the bug listings and
     * cache their data.
     *
     * order_by is the ordering used by the model.
     */
    update_from_model: function(model){
        this.handle_new_batch(model);
        this.set('current_batch', model);
        this.render();
    },

    /**
     * Return the query vars to use for the specified batch.
     * This includes the search params and the batch selector.
     */
    get_batch_query: function(config){
        var query = Y.merge(
            this.get('search_params'), {orderby: config.order_by});
        if (Y.Lang.isValue(config.memo)){
            query.memo = config.memo;
        }
        if (Y.Lang.isValue(config.start)){
            query.start = config.start;
        }
        if (config.forwards !== undefined && !config.forwards){
            query.direction = 'backwards';
        }
        return query;
    },

    /**
     * Update the display to the specified batch.
     *
     * If the batch is cached, it will be used immediately.  Otherwise, it
     * will be retrieved and cached upon retrieval.
     */
    update: function(config){
        var key = namespace.ListingNavigator.get_batch_key(config);
        var cached_batch = this.get('batches')[key];
        if (Y.Lang.isValue(cached_batch)){
            this.set('current_batch', cached_batch);
            this.render();
        }
        else {
            this.load_model(config);
        }
    },

    /**
     * Update the navigator to display the last batch.
     */
    last_batch: function(){
        this.update({
            forwards: false,
            memo: "",
            start: this.get('current_batch').last_start,
            order_by: this.get('current_batch').order_by
        });
    },

    /**
     * Update the navigator to display the first batch.
     *
     * The order_by defaults to the current ordering, but may be overridden.
     */
    first_batch: function(order_by){
        if (order_by === undefined){
            order_by = this.get('current_batch').order_by;
        }
        this.update({
            forwards: true,
            memo: null,
            start: 0,
            order_by: order_by
        });
    },

    /**
     * Update the navigator to display the next batch.
     */
    next_batch: function(){
        this.update({
            forwards: true,
            memo: this.get('current_batch').next.memo,
            start:this.get('current_batch').next.start,
            order_by: this.get('current_batch').order_by
        });
    },

    /**
     * Update the navigator to display the previous batch.
     */
    prev_batch: function(){
        this.update({
            forwards: false,
            memo: this.get('current_batch').prev.memo,
            start:this.get('current_batch').prev.start,
            order_by: this.get('current_batch').order_by
        });
    },
    /**
     * Change which fields are displayed in the batch.  Input is a config with
     * the appropriate visibility variables, such as show_bug_heat,
     * show_title, etc.
     */
    change_fields: function(config){
        this.set('field_visibility', Y.merge(this.field_visibility, config));
        this.render();
    },

    /**
     * Load the specified batch via ajax.  Display & cache on load.
     */
    load_model: function(config){
        var query = this.get_batch_query(config);
        var load_model_config = {
            on: {
                success: Y.bind(this.update_from_model, this)
            }
        };
        var context = this.get('current_batch').context;
        if (Y.Lang.isValue(this.get('io_provider'))){
            load_model_config.io_provider = this.get('io_provider');
        }
        Y.lp.client.load_model(
            context, '+bugs', load_model_config, query);
    }
});


/**
 * Rewrite all nodes with navigation classes so that they are hyperlinks.
 * Content is retained.
 */
namespace.linkify_navigation = function(){
    Y.each(['previous', 'next', 'first', 'last'], function(class_name){
        Y.all('.' + class_name).each(function(node){
            new_node = Y.Node.create('<a href="#"></a>');
            new_node.addClass(class_name);
            new_node.setContent(node.getContent());
            node.replace(new_node);
        });
    });
};

/**
 * Factory to return a ListingNavigator for the given page.
 */
namespace.ListingNavigator.from_page = function(){
    var target = Y.one('#client-listing');
    var navigation_indices = Y.all('.batch-navigation-index');
    var navigator = new namespace.ListingNavigator({
        current_url: window.location,
        cache: LP.cache,
        template: LP.mustache_listings,
        target: target,
        navigation_indices: navigation_indices
    });
    namespace.linkify_navigation();
    navigator.backwards_navigation = Y.all('.first,.previous');
    navigator.forwards_navigation = Y.all('.last,.next');
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
namespace.ListingNavigator.get_batch_key = function(config){
    return JSON.stringify([config.order_by, config.memo, config.forwards,
                           config.start]);
};

/**
 * Return the query of the specified URL in structured form.
 */
namespace.get_query = function(url){
    var querystring = Y.lp.get_url_query(url);
    return Y.QueryString.parse(querystring);
};


}, "0.1", {"requires": ["node", 'lp.client']});
