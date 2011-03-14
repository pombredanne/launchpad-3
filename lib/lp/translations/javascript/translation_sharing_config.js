
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
    initializer: function(){
        this.set('tsconfig', new TranslationSharingConfig())
    },
    select_branch: function(branch_summary){
        /* api_url, css, description, value, title */
        description = ''
        for (key in branch_summary){
            description += key + ': ' + branch_summary[key] + ', '
        }
        this.get('tsconfig').get('branch').set_link(
            branch_summary.title, branch_summary.api_uri)
        this.update()
    },
    update: function(){
        var branch = this.get('tsconfig').get('branch')
        this.update_check(branch)
    },
    update_check: function(check){
        var identifier = '#' + check.get('identifier')
        var complete_selector = identifier + ' .complete'
        var link = Y.one(complete_selector + ' a')
        link.set('href', check.get('url'))
        link.set('text', check.get('text'))
        this.set_visibility(complete_selector, check.get('complete'))
        var incomplete_selector = identifier + ' .incomplete'
        this.set_visibility(incomplete_selector, !check.get('complete'))
    },
    set_visibility: function(selector, visible){
        el = Y.one(selector)
        if (visible){
            el.removeClass('unseen')
        }
        else {
            el.addClass('unseen')
        }
    }
})
namespace.TranslationSharingController = TranslationSharingController


namespace.prepare = function(){
    var sharing_controller = new namespace.TranslationSharingController()
    sharing_controller.update()
    var config = {
        picker_activator: '#pickbranch',
        header : 'Select translation branch',
        step_title: 'Search',
        save: Y.bind('select_branch', sharing_controller)
    }
    var picker = Y.lp.app.picker.create('Branch', config)
}
}, "0.1", {"requires": ['lp.app.picker', 'oop']})
