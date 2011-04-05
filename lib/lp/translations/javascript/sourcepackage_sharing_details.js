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
    },
    clear_link: function(){
        this.set('_text', null);
        this.set('_url', null);
    }
});

namespace.LinkCheckItem = LinkCheckItem;
namespace.convert_cache = function(lp_client, cache){
    var new_cache = {}
    names = []
    for (var x in cache){
        names.push(x);
    }
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
}
namespace.usage = {
    unknown: 'Unknown',
    launchpad: 'Launchpad',
    external: 'External',
    no_applicable: 'Not Applicable'
}

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
            {identifier: 'packaging'});
        this.set('product_series', product_series);
        var usage = new CheckItem(
            {identifier: 'translation', dependency: product_series});
        this.set('translations_usage', usage);
        var branch = new LinkCheckItem(
            {identifier: 'branch', dependency: this.get('product_series')});
        this.set('branch', branch);
        var autoimport = new CheckItem(
            {identifier: 'upstream-sync', dependency: branch});
        this.set('autoimport', autoimport);
        var configuration = new CheckItem(
            {identifier: 'configuration'});
        this.set('configuration', configuration);
        this.set(
            'all_items', [product_series, usage, branch, autoimport]);
    },
});
namespace.TranslationSharingConfig = TranslationSharingConfig;


function form_url(entry, view_name){
    entry_url = Y.lp.get_url_path(entry.get('web_link'));
    return entry_url + '/' + view_name + '/++form++';
}


function update_form(overlay, entry, view_name){
    var url = form_url(entry, view_name);
    overlay.loadFormContentAndRender(url);
    overlay.render();
}


function add_activator(picker, selector){
    var element = Y.one(selector);
    element.on('click', function(e) {
        e.halt();
        this.show();
    }, picker);
    element.addClass(picker.get('picker_activator_css_class'));
}


function enum_title(form_data, name, map){
    var key = form_data[name][0];
    Y.log(key);
    var title = map[key.toLowerCase()];
    Y.log(title);
    return title;
}


function IOHandler(flash_target){
    this.flash_target = flash_target;
    this.error_handler = new Y.lp.client.ErrorHandler();
    this.error_handler.showError = function(error_msg) {
        Y.lp.app.errors.display_error(Y.one('#branch'), error_msg);
    }
}


/**
 * Return an LP client config using error_handler.
 *
 * @param next {Object} A callback to call on success.
 */
IOHandler.prototype.get_config = function(next){
    var config = {
        on:{
            success: next,
            failure: this.error_handler.getFailureHandler()
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
IOHandler.prototype.chain_config = function(){
    var last_config;
    // Each callback is bound to the next, so we use reverse order.
    for(var i = arguments.length-1; i >= 0; i--){
        if (i == arguments.length - 1)
            callback = arguments[i];
        else
            callback = Y.bind(arguments[i], this, last_config);
        last_config = this.get_config(callback);
    }
    return last_config;
}


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
        this.set('tsconfig', new TranslationSharingConfig());
        this.set('productseries', null);
        this.set('product', null);
        this.set('branch', null);
        this.set('source_package', null);
        this.set('branch_picker_config', null);
    },
    /*
     * Select the specified branch as the translation branch.
     *
     * @param branch_summary {Object} An object containing api_url, css,
     * description, value, title
     */
    configure: function(config, branch_picker_config, import_overlay,
                        usage_overlay){
        this.set('branch_picker_config', branch_picker_config);
        this.set('source_package', config['context'])
        this.set('import_overlay', import_overlay)
        this.set('usage_overlay', usage_overlay)
        this.replace_productseries(config['productseries']);
        this.replace_product(config['product']);
        this.set_branch(config['upstream_branch']);
    },
    set_productseries: function(productseries) {
        if (Y.Lang.isValue(productseries)){
            this.set('productseries', productseries)
            this.get('tsconfig').get('product_series').set_link(
                productseries.get('title'), productseries.get('web_link'))
        }
    },
    replace_productseries: function(productseries) {
        this.set_productseries(productseries);
        if (Y.Lang.isNull(productseries)){
            var autoimport_mode = namespace.autoimport_modes.no_import;
        }
        else{
            var autoimport_mode = productseries.get(
                'translations_autoimport_mode');
            var import_overlay = this.get('import_overlay');
            update_form(
                import_overlay, productseries, '+translations-settings')
        }
        this.set_autoimport_mode(autoimport_mode);
    },
    set_product: function(product){
        this.set('product', product);
        this.get('branch_picker_config')['context'] = product;
    },
    replace_product: function(product){
        this.set_product(product);
        if (Y.Lang.isNull(product)){
            var translations_usage = namespace.usage.unknown;
        }
        else {
            var translations_usage = product.get('translations_usage');
            var usage_overlay = this.get('usage_overlay');
            update_form(
                usage_overlay, product, '+configure-translations');
        }
        this.set_translations_usage(translations_usage)
    },
    set_branch: function(branch){
        this.set('branch', branch);
        var check = this.get('tsconfig').get('branch');
        if (Y.Lang.isValue(branch)){
            check.set_link(
                branch.get('unique_name'), branch.get('web_link'));
        }
        else {
            check.clear_link();
        }
    },
    set_autoimport_mode: function(mode){
        var complete = (
            mode === namespace.autoimport_modes.import_translations);
        this.get('tsconfig').get('autoimport').set('complete', complete)
    },
    set_translations_usage: function(usage){
        complete = (
            usage === namespace.usage.launchpad ||
            usage == namespace.usage.external);
        this.get('tsconfig').get('translations_usage').set('complete', complete)
    },
    select_productseries: function(productseries_summary){
        var that = this;
        var lp_client = new Y.lp.client.Launchpad();
        function save_productseries(config){
            var source_package = that.get('source_package')
            config.parameters = {
                productseries: productseries_summary['api_uri']}
            source_package.named_post('setPackaging', config)
        }
        function get_productseries(config){
            lp_client.get(productseries_summary['api_uri'], config);
        }
        function cache_productseries(config, productseries){
            that.replace_productseries(productseries);
            var branch_link = productseries.get('branch_link');
            if (branch_link === null){
                config.on.success(null);
            }
            else {
                lp_client.get(branch_link, config);
            }
        }
        function cache_branch(config, branch){
            that.set_branch(branch);
            project_link = that.get('productseries').get('project_link')
            lp_client.get(project_link, config);
        }
        function set_usage(product){
            that.replace_product(product);
            that.update();
            var check = that.get('tsconfig').get('product_series');
            that.flash_check_green(check)
        }
        var io_handler = new IOHandler('#productseries')
        save_productseries(io_handler.chain_config(
            get_productseries, cache_productseries, cache_branch, set_usage));
    },
    select_branch: function(branch_summary){
        var that = this;
        var lp_client = new Y.lp.client.Launchpad();

        /* Here begin a series of methods which each represent a step in
         * setting the branch.  They each take a config to use in an lp_client
         * call, except the last one.  This allows them to be chained
         * together.
         *
         * They take full advantage of their access to variables in the
         * closure, such as "that" and "branch_summary".
         */
        function save_branch(config){
            var productseries = that.get('productseries')
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
            that.flash_check_green(check)
        }
        var io_handler = new IOHandler('#branch')
        save_branch(io_handler.chain_config(get_branch, set_link));
    },
    /**
     * Update the display of all checklist items.
     */
    update: function(){
        var all_items = this.get('tsconfig').get('all_items');
        var overall = this.get('tsconfig').get('configuration');
        overall.set('complete', true);
        for (var i = 0; i < all_items.length; i++){
            this.update_check(all_items[i]);
            if (!all_items[i].get('complete')){
                overall.set('complete', false);
            }
        }
        this.update_check(overall);
    },
    check_identifier: function(check, complete){
        var completion = complete ? '-complete' : '-incomplete';
        return '#' + check.get('identifier') + completion
    },
    picker_selector: function(check, complete){
        return this.check_identifier(check, complete) + '-picker a';
    },
    set_check_picker: function(check, picker){
        add_activator(picker, this.picker_selector(check, true));
        add_activator(picker, this.picker_selector(check, false));
    },
    /**
     * Update the display of a single checklist item.
     */
    update_check: function(check){
        var complete = Y.one(this.check_identifier(check, true));
        var link = complete.one('.link a');
        if (link !== null){
            link.set('href', check.get('url'));
            link.set('text', check.get('text'));
        }
        complete.toggleClass('unseen', !check.get('complete'));
        complete.toggleClass('lowlight', !check.get('enabled'));
        var complete_picker = Y.one(this.picker_selector(check, true));
        if (complete_picker !== null) {
            complete_picker.toggleClass('unseen', !check.get('enabled'));
        }
        var incomplete = Y.one(this.check_identifier(check, false));
        incomplete.toggleClass('unseen', check.get('complete'));
        incomplete.toggleClass('lowlight', !check.get('enabled'))
        var incomplete_picker = Y.one(this.picker_selector(check, false));
        if (incomplete_picker !== null) {
            incomplete_picker.toggleClass('unseen', !check.get('enabled'));
        }
    },
    flash_check_green: function(check){
        var element = Y.one(this.check_identifier(check, true));
        var anim = Y.lazr.anim.green_flash({node: element});
        anim.run();
    }
});
namespace.TranslationSharingController = TranslationSharingController;


/**
 * Method to prepare the AJAX translation sharing config functionality.
 */
namespace.prepare = function(cache){
    var sharing_controller = new namespace.TranslationSharingController();
    var lp_client = new Y.lp.client.Launchpad();
    cache = namespace.convert_cache(lp_client, cache);
    var branch_picker_config = {
        picker_activator: '#branch-incomplete-picker a',
        header : 'Select translation branch',
        step_title: 'Search',
        save: Y.bind('select_branch', sharing_controller),
        context: cache['product']
    };
    var picker = Y.lp.app.picker.create(
        'BranchRestrictedOnProduct', branch_picker_config);
    /* Picker can't normally be activated by two different elements. */
    add_activator(picker, '#branch-complete-picker a');
    var productseries_picker_config = {
        picker_activator: '#packaging-complete-picker a',
        header : 'Select productseries',
        step_title: 'Search',
        save: Y.bind('select_productseries', sharing_controller),
        context: cache['product']
    };
    var productseries_picker = Y.lp.app.picker.create(
        'ProductSeries', productseries_picker_config);
    /* Picker can't normally be activated by two different elements. */
    add_activator(productseries_picker, '#packaging-incomplete-picker a');
    var import_overlay = new Y.lazr.FormOverlay({
        headerContent: '<h2>Import settings<h2>',
        centered: true,
        visible: false
    });
    import_overlay.set('form_submit_callback', function(form_data){
        Y.log(form_data['field.translations_autoimport_mode']);
        mode = enum_title(
            form_data, 'field.translations_autoimport_mode',
            namespace.autoimport_modes)
        import_overlay.hide();
        var product_series = sharing_controller.get('productseries');
        product_series.set('translations_autoimport_mode', mode);
        handler = new IOHandler();
        function update_controller(){
            sharing_controller.set_autoimport_mode(mode);
            sharing_controller.update();
            var check = sharing_controller.get('tsconfig').get('autoimport');
            sharing_controller.flash_check_green(check)
        }
        /* XXX: AaronBentley 2011-04-04 bug=369293: Avoid 412 on repeated
         * changes.  This does not increase the risk of changing from a
         * stale value, because the staleness check is not reasonable.
         * The user is changing from the default shown in the form, not
         * the value stored in productseries.
         */
        product_series.removeAttr('http_etag')
        product_series.lp_save(handler.chain_config(update_controller));
    });
    var autoimport = sharing_controller.get('tsconfig').get('autoimport');
    sharing_controller.set_check_picker(autoimport, import_overlay);
    var usage_overlay = new Y.lazr.FormOverlay({
        headerContent: '<h2>Usage settings<h2>',
        centered: true,
        visible: false
    });
    usage_overlay.set('form_submit_callback', function(form_data){
        usage_overlay.hide();
        usage = enum_title(
            form_data, 'field.translations_usage', namespace.usage);
        var product = sharing_controller.get('product');
        product.set('translations_usage', usage);
        handler = new IOHandler();
        function update_controller(){
            sharing_controller.replace_product(product);
            sharing_controller.update();
            var check = sharing_controller.get('tsconfig').get(
                'translations_usage');
            sharing_controller.flash_check_green(check)
        }
        /* XXX: AaronBentley 2011-04-04 bug=369293: Avoid 412 on repeated
         * changes.  This does not increase the risk of changing from a
         * stale value, because the staleness check is not reasonable.
         * The user is changing from the default shown in the form, not
         * the value stored in productseries.
         */
        product.removeAttr('http_etag')
        product.lp_save(handler.chain_config(update_controller));
    });
    var usage = sharing_controller.get('tsconfig').get('translations_usage');
    sharing_controller.set_check_picker(usage, usage_overlay);
    sharing_controller.configure(
        cache, branch_picker_config, import_overlay, usage_overlay);
    sharing_controller.update();
};
}, "0.1", {"requires": ['lp', 'lp.app.errors', 'lp.app.picker', 'oop', 'lp.client']})
