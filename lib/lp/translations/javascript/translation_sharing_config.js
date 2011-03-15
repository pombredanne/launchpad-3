
YUI.add('lp.translations.translation_sharing_config', function(Y) {
var namespace = Y.namespace('lp.translations.translation_sharing_config');

function CheckItem(config){
    CheckItem.superclass.constructor.apply(this, arguments)
}
CheckItem.ATTRS = {
    dependency: {value: null},
    enabled: {
        getter: function(){
            if (Y.Lang.isNull(this.get('dependency'))){
                return true;
            }
            return this.get('dependency').get('complete');
        }
    },
    identifier: undefined
}
Y.extend(CheckItem, Y.Base, {
})

namespace.CheckItem = CheckItem

function LinkCheckItem(){
    LinkCheckItem.superclass.constructor.apply(this, arguments)
}
LinkCheckItem.ATTRS = {
    complete: {getter:
        function() {
            return !Y.Lang.isNull(this.get('_text'))
        }
    },
    _text: {value: null},
    text: {getter:
        function(){
            return this.get('_text')
        }
    },
    _url: {value: null},
    url: { getter:
        function(){
            return this.get('_url')
        }
    },
}
Y.extend(LinkCheckItem, CheckItem, {
    set_link: function(text, url){
        this.set('_text', text);
        this.set('_url', url);
    }
})

namespace.LinkCheckItem = LinkCheckItem

function TranslationSharingConfig (config){
    TranslationSharingConfig.superclass.constructor.apply(this, arguments)
}
Y.extend(TranslationSharingConfig, Y.Base, {
    initializer: function(){
        var product_series = new LinkCheckItem({identifier: 'product-series'})
        this.set('product_series', product_series)
        var usage = new CheckItem(
            {identifier: 'usage', dependency: product_series});
        this.set('translation_usage', usage);
        var branch = new LinkCheckItem(
            {identifier: 'branch', dependency: this.get('product_series')})
        this.set('branch', branch);
        var autoimport = new CheckItem(
            {identifier: 'autoimport', dependency: branch})
        this.set('autoimport', autoimport);
        this.set('all_items', [product_series, usage, branch, autoimport])
    }
})
namespace.TranslationSharingConfig = TranslationSharingConfig

function TranslationSharingController (config){
    TranslationSharingController.superclass.constructor.apply(this, arguments)
}
Y.extend(TranslationSharingController, Y.Base, {
    initializer: function(source_package){
        this.set('source_package', source_package)
        this.set('productseries_link', source_package['productseries_link'])
        this.set('tsconfig', new TranslationSharingConfig())
    },
    select_branch: function(branch_summary){
        /* api_url, css, description, value, title */
        var lp_client = new Y.lp.client.Launchpad();
        var error_handler = new Y.lp.client.ErrorHandler()
        error_handler.showError = function(error_msg) {
            Y.lp.app.errors.display_error(
                Y.one('#branch'), error_msg
            )
        }
        var default_config = {
            on:{
                failure: error_handler.getFailureHandler()
            }
        }
        var config = Y.clone(default_config);
        config['on']['success'] = Y.bind(
            'save_branch', this, default_config, branch_summary)
        lp_client.get(this.get('productseries_link'), config);
    },
    save_branch: function(default_config, branch_summary, productseries){
        function get_config(next){
            var config = Y.clone(default_config);
            config['on']['success'] = next;
            return config;
        }
        function get_branch(config){
            var lp_client = new Y.lp.client.Launchpad();
            lp_client.get(branch_summary['api_uri'], config);
        }
        function set_link(branch){
            this.get('tsconfig').get('branch').set_link(
                branch_summary.title, branch.get('web_link')); this.update()
        }
        var get_branch_config = get_config(Y.bind(set_link, this))
        productseries.set('branch_link', branch_summary['api_uri']);
        var config = get_config(Y.bind(get_branch, this, get_branch_config));
        productseries.lp_save(config)
    },
    update: function(){
        var branch = this.get('tsconfig').get('branch')
        this.update_check(branch)
    },
    update_check: function(check){
        var section = Y.one('#' + check.get('identifier'))
        var complete = section.one('.complete')
        var link = complete.one('a')
        link.set('href', check.get('url'))
        link.set('text', check.get('text'))
        complete.toggleClass('unseen', !check.get('complete'))
        incomplete = section.one('.incomplete')
        incomplete.toggleClass('unseen', check.get('complete'))
    },
})
namespace.TranslationSharingController = TranslationSharingController


namespace.prepare = function(source_package){
    var sharing_controller = new namespace.TranslationSharingController(
        source_package)
    sharing_controller.update()
    var config = {
        picker_activator: '#pickbranch',
        header : 'Select translation branch',
        step_title: 'Search',
        save: Y.bind('select_branch', sharing_controller)
    }
    var picker = Y.lp.app.picker.create('Branch', config)
}
}, "0.1", {"requires": ['lp.app.errors', 'lp.app.picker', 'oop']})
