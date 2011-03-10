YUI.add('lp.translations.translation_sharing_config', function(Y) {
var namespace = Y.namespace('lp.translations.translation_sharing_config');
function TranslationSharingConfig (config){
    TranslationSharingConfig.superclass.constructor.apply(this, arguments)
}
TranslationSharingConfig.ATTRS = {
    _product_series: {value: null},
    product_series: {
        getter: function(){
            return this.get('_product_series')
        }
    },
    branch_enabled: {
        getter: function(){
            return !Y.Lang.isNull(this.get('_product_series'))
        }
    },
    _product: {value: null},
    translation_group_enabled: {
        getter: function(){
            return !Y.Lang.isNull(this.get('_product'))
        }
    },
    translation_permission_enabled: {
        getter: function(){
            return this.get('translation_group_enabled')
        }
    },
    translation_usage_enabled: {
        getter: function(){
            return this.get('translation_group_enabled')
        }
    },
    branch: {value: null},
    autoimport_enabled: {getter: function(){
        return !Y.Lang.isNull(this.get('branch'))
    }}
}
Y.extend(TranslationSharingConfig, Y.Base, {
    set_product_series: function(product_series, product){
        this.set('_product', product);
        this.set('_product_series', product_series);
    }
})
namespace.TranslationSharingConfig = TranslationSharingConfig
}, "0.1", {"requires": ["base"]})
