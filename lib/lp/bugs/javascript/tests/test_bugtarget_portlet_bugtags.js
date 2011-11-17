YUI().use('lp.testing.runner', 'lp.testing.mockio', 'test', 'console', 
          'lp.client', 'node-event-simulate', 'lp.bugs.bugtask.taglist', 
    function(Y) {

    var module = Y.lp.bugs.bugtask.taglist;
    var suite = new Y.Test.Suite("Bug tags portlet Tests");

    suite.add(new Y.Test.Case({
        name: 'Tags list',

        tearDown: function() {
                Y.one('.portletBody').remove();
            },
        
        test_io_url: function() {
            var mockio = new Y.lp.testing.mockio.MockIo();
            module.setup_taglist({io_provider: mockio});
            mockio.success({
                responseText: '<div class="portletBody"><div class="section">'+
                              '<h2>Tags</h2><ul class="tag-list">'+
                              '</ul></div></div>',
                responseHeaders: {'Content-type': 'text/html'}});
            Y.Assert.areEqual('/launchpad/+bugtarget-portlet-tags-content',
                              mockio.last_request.url);
            },
        
        test_no_tags: function() {
            // Test when there are no tags
            var mockio = new Y.lp.testing.mockio.MockIo();
            module.setup_taglist({io_provider: mockio});
            mockio.success({
                responseText: '<div class="portletBody"><div class="section">'+
                              '<h2>Tags</h2><ul class="tag-list">'+
                              '</ul></div></div>',
                responseHeaders: {'Content-type': 'text/html'}});
            
            var tags = Y.all('.tag-list li');
            var show_more_link = Y.one('#show-more-tags-link');
            var show_less_link = Y.one('#show-less-tags-link');
            
            // Check the list is empty
            Y.Assert.areEqual(0, tags.size());
            
            // Check show more link is hidden
            Y.Assert.isTrue(show_more_link.hasClass('hidden'));
            
            // Check show less link is hidden
            Y.Assert.isTrue(show_less_link.hasClass('hidden'));
            },
        
        test_twenty_tags_or_less: function() {
            // Test when there are twenty tags or less
            var mockio = new Y.lp.testing.mockio.MockIo();
            module.setup_taglist({io_provider: mockio});
            mockio.success({
                responseText: '<div class="portletBody"><div class="section">'+
                              '<h2>Tags</h2><ul class="tag-list">'+
                              '<li><span class="tag-count">4</span>'+
                              '<a href="+bugs?field.tag=crash">lorem</a></li>'+
                              '<li><span class="tag-count">3</span>'+
                              '<a href="+bugs?field.tag=crash">ipsum</a></li>'+
                              '<li><span class="tag-count">2</span>'+
                              '<a href="+bugs?field.tag=crash">dolor</a></li>'+
                              '<li><span class="tag-count">1</span>'+
                              '<a href="+bugs?field.tag=crash">sit</a></li>'+
                              '</ul></div></div>',
                responseHeaders: {'Content-type': 'text/html'}});
            
            var tags = Y.all('.tag-list li');
            var show_more_link = Y.one('#show-more-tags-link');
            var show_less_link = Y.one('#show-less-tags-link');
            
            // Check the list has twenty tags or less
            Y.assert(tags.size() <= 20);
            
            // Check show more link is hidden
            Y.Assert.isTrue(show_more_link.hasClass('hidden'));
            
            // Check show less link is hidden
            Y.Assert.isTrue(show_less_link.hasClass('hidden'));
            },

        test_more_than_twenty_tags: function() {
            // Test when there are more than twenty tags
            var mockio = new Y.lp.testing.mockio.MockIo();
            module.setup_taglist({io_provider: mockio});
            mockio.success({
                responseText: '<div class="portletBody"><div class="section">'+
                              '<h2>Tags</h2><ul class="tag-list">'+
                              '<li><span class="tag-count">4</span>'+
                              '<a href="+bugs?field.tag=crash">lorem</a></li>'+
                              '<li><span class="tag-count">3</span>'+
                              '<a href="+bugs?field.tag=crash">ipsum</a></li>'+
                              '<li><span class="tag-count">2</span>'+
                              '<a href="+bugs?field.tag=crash">dolor</a></li>'+
                              '<li><span class="tag-count">1</span>'+
                              '<a href="+bugs?field.tag=crash">sit</a></li>'+
                              '<li><span class="tag-count">0</span>'+
                              '<a href="+bugs?field.tag=crash">amet</a></li>'+
                              '<li><span class="tag-count">0</span>'+
                              '<a href="+bugs?field.tag=crash">amet</a></li>'+
                              '<li><span class="tag-count">0</span>'+
                              '<a href="+bugs?field.tag=crash">amet</a></li>'+
                              '<li><span class="tag-count">0</span>'+
                              '<a href="+bugs?field.tag=crash">amet</a></li>'+
                              '<li><span class="tag-count">0</span>'+
                              '<a href="+bugs?field.tag=crash">amet</a></li>'+
                              '<li><span class="tag-count">0</span>'+
                              '<a href="+bugs?field.tag=crash">amet</a></li>'+
                              '<li><span class="tag-count">0</span>'+
                              '<a href="+bugs?field.tag=crash">amet</a></li>'+
                              '<li><span class="tag-count">0</span>'+
                              '<a href="+bugs?field.tag=crash">amet</a></li>'+
                              '<li><span class="tag-count">0</span>'+
                              '<a href="+bugs?field.tag=crash">amet</a></li>'+
                              '<li><span class="tag-count">0</span>'+
                              '<a href="+bugs?field.tag=crash">amet</a></li>'+
                              '<li><span class="tag-count">0</span>'+
                              '<a href="+bugs?field.tag=crash">amet</a></li>'+
                              '<li><span class="tag-count">0</span>'+
                              '<a href="+bugs?field.tag=crash">amet</a></li>'+
                              '<li><span class="tag-count">0</span>'+
                              '<a href="+bugs?field.tag=crash">amet</a></li>'+
                              '<li><span class="tag-count">0</span>'+
                              '<a href="+bugs?field.tag=crash">amet</a></li>'+
                              '<li><span class="tag-count">0</span>'+
                              '<a href="+bugs?field.tag=crash">amet</a></li>'+
                              '<li><span class="tag-count">0</span>'+
                              '<a href="+bugs?field.tag=crash">amet</a></li>'+
                              '<li><span class="tag-count">0</span>'+
                              '<a href="+bugs?field.tag=crash">amet</a></li>'+
                              '<li><span class="tag-count">0</span>'+
                              '<a href="+bugs?field.tag=crash">amet</a></li>'+
                              '</ul></div></div>',
                responseHeaders: {'Content-type': 'text/html'}});
            
            var tags = Y.all('.tag-list li');
            var show_more_link = Y.one('#show-more-tags-link');
            var show_less_link = Y.one('#show-less-tags-link');
            var tag_count = tags.size()
            
            // Check the list has more than twenty tags
            Y.assert(tag_count > 20);
            
            // Check that only twenty tags are visible
            Y.Assert.areEqual(20, tag_count - tags.filter('.hidden').size());
            
            // Check show less link is hidden
            Y.Assert.isTrue(show_less_link.hasClass('hidden'));
            
            // Check show more link is visible
            Y.Assert.isFalse(show_more_link.hasClass('hidden'));
            
            // Click the show more link
            show_more_link.simulate('click');
            
            // Check that all the tags are now visible
            Y.Assert.areEqual(0, tags.filter('.hidden').size());
            
            // Check show more link is now hidden
            Y.Assert.isTrue(show_more_link.hasClass('hidden'));
            
            // Check show less link is now visible
            Y.Assert.isFalse(show_less_link.hasClass('hidden'));
            
            // Click the show less link
            show_less_link.simulate('click');
            
            // Check that only twenty tags are now visible
            Y.Assert.areEqual(20, tag_count - tags.filter('.hidden').size());
            
            // Check show less link is now hidden
            Y.Assert.isTrue(show_less_link.hasClass('hidden'));
            
            // Check show more link is now visible
            var show_more_link = Y.one('#show-more-tags-link');
            Y.Assert.isFalse(show_more_link.hasClass('hidden'));
            },
        }));

    Y.lp.testing.Runner.run(suite);
});
