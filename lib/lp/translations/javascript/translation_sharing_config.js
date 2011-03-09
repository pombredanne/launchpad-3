YUI.add('lp.translations.translation_sharing_config', function(Y) {
var namespace = Y.namespace('lp.translations.translation_sharing_config');
function TranslationSharingConfig (config){
    TranslationSharingConfig.superclass.constructor.apply(this, arguments)
}
TranslationSharingConfig.ATTRS = {
    product_series: {value: null},
    branch_enabled: {
        getter: function(){
            return !Y.Lang.isNull(this.get('product_series'))
        }
    },
    product: {value: null},
    translation_group_enabled: {
        getter: function(){
            return !Y.Lang.isNull(this.get('product'))
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
})
namespace.TranslationSharingConfig = TranslationSharingConfig
}, "0.1", {"requires": ["base"]})
