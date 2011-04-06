/* Copyright 2011 Canonical Ltd.  This software is licensed under the
 * GNU Affero General Public License version 3 (see the file LICENSE).
 */

YUI.add('lp.translations.sourcepackage_sharing_details', function(Y) {
var namespace = Y.namespace('lp.translations.sourcepackage_sharing_details');

/**
 * This class represents the state of a checklist item.
 */
function CheckItem(config){
    CheckItem.superclass.constructor.apply(this, arguments);
}
CheckItem.ATTRS = {
    complete: {value: false},
    // Optional reference to an item that must be completed before setting
    // this.
    dependency: {value: null},
    // True if this item is enabled.
    enabled: {
        getter: function(){
            if (Y.Lang.isNull(this.get('dependency'))){
                return true;
            }
            return this.get('dependency').get('complete');
        }
    },
    // The HTML identifier of the item.
    identifier: null
}
Y.extend(CheckItem, Y.Base, {
})

namespace.CheckItem = CheckItem;

/**
 * This class reflects the state of a Checklist item that holds a link.
 */
function LinkCheckItem(){
    LinkCheckItem.superclass.constructor.apply(this, arguments)
}
LinkCheckItem.ATTRS = {
    // This item is complete if _text is set.
    complete: {getter:
        function() {
            return !Y.Lang.isNull(this.get('_text'))
        }
    },
    // _text is unset by default.
    _text: {value: null},
    // text is read-only.
    text: {getter:
        function(){
            return this.get('_text');
        }
    },
    // _url is unset by default.
    _url: {value: null},
    // text is read-only.
    url: { getter:
        function(){
            return this.get('_url');
        }
    },
}
Y.extend(LinkCheckItem, CheckItem, {
    /**
     * Set the text and URL of the link for this LinkCheckItem.
     */
    set_link: function(text, url){
        this.set('_text', text);
        this.set('_url', url);
    }
});

namespace.LinkCheckItem = LinkCheckItem;
namespace.convert_cache = function(lp_client, cache){
    var new_cache = {};
    for (var key in cache){
        var value = cache[key];
        if (value !== null)
            value = lp_client.wrap_resource(value.self_link, value);
        new_cache[key] = value;
    }
    return new_cache;
}


namespace.autoimport_modes = {
    no_import: 'None',
    import_templates: 'Import template files',
    import_translations: 'Import template and translation files'
};


namespace.usage = {
    unknown: 'Unknown',
    launchpad: 'Launchpad',
    external: 'External',
    no_applicable: 'Not Applicable'
};

/**
 * This class represents the state of the translation sharing config
 * checklist.
 */
function TranslationSharingConfig (config){
    TranslationSharingConfig.superclass.constructor.apply(this, arguments)
}
Y.extend(TranslationSharingConfig, Y.Base, {
    initializer: function(){
        var product_series = new LinkCheckItem(
            {identifier: 'product-series'});
        this.set('product_series', product_series);
        var usage = new CheckItem(
            {identifier: 'usage', dependency: product_series});
        this.set('translations_usage', usage);
        var branch = new LinkCheckItem(
            {identifier: 'branch', dependency: this.get('product_series')});
        this.set('branch', branch);
        var autoimport = new CheckItem(
            {identifier: 'autoimport', dependency: branch});
        this.set('autoimport', autoimport);
        this.set('all_items', [product_series, usage, branch, autoimport]);
    }
});
namespace.TranslationSharingConfig = TranslationSharingConfig;

/**
 * This class is the controller for updating the TranslationSharingConfig.
 * It handles updating the HTML and the DB model.
 */
function TranslationSharingController (config){
    TranslationSharingController.superclass.constructor.apply(
        this, arguments);
}
Y.extend(TranslationSharingController, Y.Base, {
    initializer: function(source_package){
        this.set('source_package', source_package);
        this.set('tsconfig', new TranslationSharingConfig());
        this.set('productseries', null);
        this.set('branch', null);
    },
    /*
     * Select the specified branch as the translation branch.
     *
     * @param branch_summary {Object} An object containing api_url, css,
     * description, value, title
     */
    configure: function(config){
        this.set_productseries(config['productseries'])
        if (Y.Lang.isNull(config['productseries'])){
            var autoimport_mode = namespace.autoimport_modes.no_import;
            var translations_usage = namespace.usage.unknown;
        }
        else {
            var autoimport_mode = config['productseries'].get(
                'translations_autoimport_mode');
            var translations_usage = config['product'].get(
                'translations_usage');
        }
        this.set_autoimport_mode(autoimport_mode);
        this.set_translations_usage(translations_usage);
        this.set_branch(config['upstream_branch']);
    },
    set_productseries: function(productseries) {
        if (Y.Lang.isValue(productseries)){
            this.set('productseries', productseries);
            this.get('tsconfig').get('product_series').set_link(
                productseries.get('title'), productseries.get('web_link'));
        }
    },
    set_branch: function(branch){
        this.set('branch', branch);
        if (Y.Lang.isValue(branch)){
            this.get('tsconfig').get('branch').set_link(
                branch.get('unique_name'), branch.get('web_link'));
        }
    },
    set_autoimport_mode: function(mode){
        complete = (mode === namespace.autoimport_modes.import_translations);
        this.get('tsconfig').get('autoimport').set('complete', complete);
    },
    set_translations_usage: function(usage){
        complete = (
            usage === namespace.usage.launchpad ||
            usage == namespace.usage.external);
        var usage_check = this.get('tsconfig').get('translations_usage');
        usage_check.set('complete', complete);
    },
    select_branch: function(branch_summary){
        var that = this;
        var lp_client = new Y.lp.client.Launchpad();
        var error_handler = new Y.lp.client.ErrorHandler();
        error_handler.showError = function(error_msg) {
            Y.lp.app.errors.display_error(Y.one('#branch'), error_msg);
        }
        /**
         * Return an LP client config using error_handler.
         *
         * @param next {Object} A callback to call on success.
         */
        function get_config(next){
            var config = {
                on:{
                    success: next,
                    failure: error_handler.getFailureHandler()
                }
            };
            return config;
        }
        /**
         * Return an LP client config that will call the specified callbacks
         * in sequence, using error_handler.
         *
         * @param next {Object} A callback to call on success.
         */
        function chain_config(){
            var last_config;
            // Each callback is bound to the next, so we use reverse order.
            for(var i = arguments.length-1; i >= 0; i--){
                if (i == arguments.length - 1)
                    callback = arguments[i];
                else
                    callback = Y.bind(arguments[i], this, last_config);
                last_config = get_config(callback);
            }
            return last_config;
        }

        /* Here begin a series of methods which each represent a step in
         * setting the branch.  They each take a config to use in an lp_client
         * call, except the last one.  This allows them to be chained
         * together.
         *
         * They take full advantage of their access to variables in the
         * closure, such as "that" and "branch_summary".
         */
        function save_branch(config){
            var productseries = that.get('productseries');
            productseries.set('branch_link', branch_summary['api_uri']);
            productseries.lp_save(config);
        }
        function get_branch(config){
            lp_client.get(branch_summary['api_uri'], config);
        }
        function set_link(branch){
            that.set_branch(branch);
            that.update();
            var check = that.get('tsconfig').get('branch');
            var element = Y.one(that.check_selector(check, true));
            var anim = Y.lazr.anim.green_flash({node: element});
            anim.run();
        }
        save_branch(chain_config(get_branch, set_link));
    },
    /**
     * Update the display of all checklist items.
     */
    update: function(){
        var branch = this.get('tsconfig').get('branch');
        this.update_check(branch);
    },
    check_selector: function(check, complete){
        var completion = complete ? '-complete' : '-incomplete';
        return '#' + check.get('identifier') + completion;
    },
    /**
     * Update the display of a single checklist item.
     */
    update_check: function(check){
        var complete = Y.one(this.check_selector(check, true));
        var link = complete.one('a.link');
        link.set('href', check.get('url'));
        link.set('text', check.get('text'));
        complete.toggleClass('unseen', !check.get('complete'));
        var incomplete = Y.one(this.check_selector(check, false));
        incomplete.toggleClass('unseen', check.get('complete'));
        incomplete.toggleClass('lowlight', !check.get('enabled'));
    },
});
namespace.TranslationSharingController = TranslationSharingController;


/**
 * Method to prepare the AJAX translation sharing config functionality.
 */
namespace.prepare = function(source_package, cache){
    var sharing_controller = new namespace.TranslationSharingController(
        source_package);
    var lp_client = new Y.lp.client.Launchpad();
    cache = namespace.convert_cache(lp_client, cache);
    sharing_controller.configure(cache);
    sharing_controller.update();
    var config = {
        picker_activator: '#branch-incomplete-picker a',
        header : 'Select translation branch',
        step_title: 'Search',
        save: Y.bind('select_branch', sharing_controller),
        context: cache['product']
    };
    var picker = Y.lp.app.picker.create('BranchRestrictedOnProduct', config);
    var element = Y.one('#branch-complete-picker a');
    /* Copy-pasted because picker can't normally be activated by two different
    /* elements. */
    element.on('click', function(e) {
        e.halt();
        this.show();
    }, picker);
    element.addClass(picker.get('picker_activator_css_class'));

};
}, "0.1", {"requires": ['lp.app.errors', 'lp.app.picker', 'oop', 'lp.client']})
