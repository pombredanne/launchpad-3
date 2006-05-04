LARGE_PNG:=$(patsubst %.dia,%.png,$(shell cd large-dia; ls *.dia))
ALL_PNG:=$(patsubst %.dia,%.png,$(shell cd dia; ls *.dia)) $(LARGE_PNG)

html: png bazaar.html

ps: bazaar.ps

png: $(ALL_PNG)

clean:
	rm -f bazaar.html
	rm -f *~
	rm -f bazaar.ps
	rm -f *.png

%.html: html.xsl %.tmml
	xsltproc $^ > $@

%.ps: %.tmml png
	texmacs -c $< $@ -x '(quit-TeXmacs)'

%.tmml: %.tm
	texmacs -c $< $@  -x '(quit-TeXmacs))'

%.png: dia/%.dia
	rm -f $@
	dia -e $@ $^ > /dev/null 2>&1

png_size=$(shell echo $(1) | join -o 2.2 - large-dia/sizes)

%.png: large-dia/%.dia
	rm -f $@
	dia -e $@ -s $(call png_size,$@) $< > /dev/null 2>&1

large-dia/sizes: $(LARGE_PNG)
	./write-sizes $@ $^


.PHONY: html ps png clean
