<?xml version="1.0" encoding="ISO-8859-1"?>

<xsl:stylesheet
    version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns="http://www.w3.org/1999/xhtml">

<xsl:output method="xml" version="1.0"
    doctype-public="-//W3C//DTD XHTML 1.0 Strict//EN"
    doctype-system="http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd"/>

<!-- Print an error when an element is not matched -->

<xsl:template match="*">
  <div class="error">Unmatched element</div>
</xsl:template>


<!-- Root templates -->

<xsl:template match="/TeXmacs">
  <xsl:apply-templates/>
</xsl:template>

<xsl:template match="/TeXmacs/*"/>

<xsl:template match="/TeXmacs/body">
  <html lang="en" xml:lang="en">
    <head>
      <title><xsl:value-of select="tm-par/doc-data/doc-title"/></title>
      <link  rel="stylesheet" href="texmacs.css" type="text/css"/>
    </head>
    <body>
      <xsl:apply-templates/>
    </body>
  </html>
</xsl:template>


<!-- Paragraph formating -->

<xsl:template match="body/tm-par">
  <p><xsl:apply-templates/></p>
</xsl:template>

<xsl:template match="no-page-break|no-page-break_42_"/>

<xsl:template match="new-page|new-page_42_"/>


<!-- Sectioning -->

<xsl:template match="tm-par[doc-data]|doc-data">
  <xsl:apply-templates/>
</xsl:template>

<xsl:template match="doc-title">
  <h1><xsl:apply-templates/></h1>
</xsl:template>

<xsl:template match="tm-par[section|subsection|subsubsection]">
  <xsl:apply-templates/>
</xsl:template>

<xsl:template match="section">
  <h2>
    <xsl:value-of select="count(preceding::section) + 1"/>
    <xsl:text>. </xsl:text>
    <xsl:apply-templates/>
  </h2>
</xsl:template>

<xsl:template match="subsection">
  <h3>
    <xsl:value-of select="count(preceding::section)"/>
    <xsl:text>.</xsl:text>
    <xsl:value-of select="count(preceding::subsection[generate-id(preceding::section[1]) = generate-id(current()/preceding::section[1])]) + 1"/>
    <xsl:text>. </xsl:text>
    <xsl:apply-templates/>
  </h3>
</xsl:template>

<xsl:template match="subsubsection">
  <h4>
    <xsl:value-of select="count(preceding::section)"/>
    <xsl:text>.</xsl:text>
    <xsl:value-of select="count(preceding::subsection[generate-id(preceding::section[1]) = generate-id(current()/preceding::section[1])])"/>
    <xsl:text>.</xsl:text>
    <xsl:value-of select="count(preceding::subsubsection[generate-id(preceding::subsection[1]) = generate-id(current()/preceding::subsection[1])]) + 1"/>
    <xsl:text>. </xsl:text>
    <xsl:apply-templates/>
  </h4>
</xsl:template>

<xsl:template match="paragraph">
  <strong><xsl:apply-templates/><xsl:text> </xsl:text></strong>
</xsl:template>


<!-- Unordered lists -->

<xsl:template match="tm-par[itemize]">
  <xsl:apply-templates/>
</xsl:template>

<xsl:template match="itemize">
  <ul><xsl:apply-templates/></ul>
</xsl:template>

<xsl:template match="itemize/tm-par[item]">
  <li><xsl:apply-templates/></li>
</xsl:template>

<xsl:template match="itemize/tm-par/item"/>


<!-- Description lists -->

<xsl:template match="tm-par[description-long|description-dash]">
  <xsl:apply-templates/>
</xsl:template>

<xsl:template match="description-long|description-dash">
  <dl><xsl:apply-templates/></dl>
</xsl:template>

<xsl:template match="description-long/tm-par[item_42_]">
  <xsl:call-template name="description-para"/>
</xsl:template>

<xsl:template match="description-dash/tm-par[item_42_]">
  <xsl:call-template name="description-para"/>
</xsl:template>

<xsl:template name="description-para">
  <dt><xsl:apply-templates select="item_42_/child::node()"/></dt>
  <dd><xsl:apply-templates/></dd>
</xsl:template>

<xsl:template match="description-long/tm-par/item_42_"/>

<xsl:template match="description-dash/tm-par/item_42_"/>

 
<!-- Figures -->

<xsl:template match="tm-par[big-figure]|big-figure/tm-arg">
  <xsl:apply-templates/>
</xsl:template>

<xsl:template match="big-figure">
  <div class="big-figure">
    <div class="figure-body">
      <xsl:apply-templates select="tm-arg[1]"/>
    </div>
    <div class="figure-caption">
      <b>
	<xsl:text>Figure </xsl:text>
	<xsl:value-of select="count(preceding::big-figure) + 1"/>
	<xsl:text>: </xsl:text>
      </b>
      <xsl:apply-templates select="tm-arg[2]"/>
    </div>
  </div>
</xsl:template>

<xsl:template match="postscript">
  <img>
    <xsl:attribute name="src">
      <xsl:value-of select="tm-arg[1]"/>
    </xsl:attribute>
    <xsl:attribute name="alt">
      <xsl:value-of select="tm-arg[1]"/>
    </xsl:attribute>
  </img>
</xsl:template>


<!-- Text styling -->

<xsl:template match="tm-par[with/tm-par]">
  <xsl:apply-templates/>
</xsl:template>

<xsl:template match="with[@color='dark red']">
  <span class="dark-red"><xsl:apply-templates/></span>
</xsl:template>

<xsl:template match="with[@color='dark red'][tm-par]">
  <p class="dark-red">
    <xsl:apply-templates select="tm-par/child::node()"/>
  </p>
</xsl:template>

<xsl:template match="with[@color='red']">
  <span class="red"><xsl:apply-templates/></span>
</xsl:template>

<xsl:template match="with[@font-shape='small-caps']">
  <span class="small-caps"><xsl:apply-templates/></span>
</xsl:template>

<xsl:template match="with[@font-shape='italic']">
  <i><xsl:apply-templates/></i>
</xsl:template>

<xsl:template match="verbatim">
  <tt><xsl:apply-templates/></tt>
</xsl:template>

<xsl:template match="em">
  <em><xsl:apply-templates/></em>
</xsl:template>

<!-- Hyperlinks -->

<xsl:template match="hlink">
  <a>
    <xsl:attribute name="href">
    <xsl:value-of select="tm-arg[2]"/>
    </xsl:attribute>
    <xsl:apply-templates select="tm-arg[1]"/>
  </a>
</xsl:template>

<xsl:template match="hlink/tm-arg">
  <xsl:apply-templates/>
</xsl:template>

</xsl:stylesheet>
