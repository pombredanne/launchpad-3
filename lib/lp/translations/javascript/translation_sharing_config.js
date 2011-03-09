YUI.add('lp.translations.translation_sharing_config', function(Y) {
var namespace = Y.namespace('lp.translations.translation_sharing_config');
function TranslationSharingConfig (config){
    TranslationSharingConfig.superclass.constructor.apply(this, arguments)
}
TranslationSharingConfig.ATTRS = {
    product_series: {value: null},
    branch_enabled: {getter: function(){
        return !Y.Lang.isNull(this.get('product_series'))
        }
    }
}
Y.extend(TranslationSharingConfig, Y.Base, {
})
namespace.TranslationSharingConfig = TranslationSharingConfig
}, "0.1", {"requires": ["base"]})
