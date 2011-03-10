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
    }
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
        this.set('product_series', new LinkCheckItem())
        var usage = new CheckItem({dependency: this.get('product_series')});
        this.set('translation_usage', usage);
        branch = new LinkCheckItem({dependency: this.get('product_series')})
        this.set('branch', branch);
        this.set('autoimport', new CheckItem({dependency: branch}));
    }
})
namespace.TranslationSharingConfig = TranslationSharingConfig
}, "0.1", {"requires": ["base"]})
