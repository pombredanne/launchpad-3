<!-- Launchpad customizations common to all our MHonArc-generated
     mailing list archives.

     See http://www.mhonarc.org/MHonArc/doc/mhonarc.html and
     http://www.mhonarc.org/MHonArc/doc/faq/, they are your friends.

     http://www.mhonarc.org/MHonArc/doc/resources.html#index is
     especially your friend, when all others have abandoned you.  -->

<!-- Basic parameters. -->
<MAIN>
<THREAD>
<SORT>
<REVERSE>
<TREVERSE>
<NODOC>

<!-- Use multi-page indexes.
     See http://www.mhonarc.org/MHonArc/doc/resources/multipg.html -->
<MULTIPG>
<IDXSIZE>
200
</IDXSIZE>

<!-- Define a custom resource variable to represent this mailing list.
     This depends on $MLNAME$ having been set already, presumably on
     the command line via '-definevar'.  See 
     http://www.mhonarc.org/MHonArc/doc/resources/definevar.html. -->
<DefineVar>
ML-FULL-TITLE
<a href="http://launchpad.net/~$ML-NAME$">$ML-NAME$</a> mailing list archive
</DefineVar>

<!-- Title for the main page. -->
<TITLE>
$ML-FULL-TITLE$ (by date)
</TITLE>

<!-- Title for the thread page. -->
<TTITLE>
$ML-FULL-TITLE$ (by thread)
</TTITLE>

<IDXLABEL>
date index
</IDXLABEL>

<TIDXLABEL>
thread index
</TIDXLABEL>

<!-- What do the next/prev links look like? -->
<NEXTPGLINK>
<a href="$PG(NEXT)$">Next&rarr</a>
</NEXTPGLINK>
<NEXTPGLINKIA>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
</NEXTPGLINKIA>
<TNEXTPGLINK>
<a href="$PG(TNEXT)$">Next&rarr</a>
</TNEXTPGLINK>
<TNEXTPGLINKIA>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
</TNEXTPGLINKIA>
<PREVPGLINK>
<a href="$PG(PREV)$">&larr;Prev</a>
</PREVPGLINK>
<PREVPGLINKIA>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
</PREVPGLINKIA>
<TPREVPGLINK>
<a href="$PG(TPREV)$">&larr;Prev</a>
</TPREVPGLINK>
<TPREVPGLINKIA>
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
</TPREVPGLINKIA>

<!-- Formatting for the start of list page.
     See http://www.mhonarc.org/MHonArc/doc/resources/listbegin.html. -->
<LISTBEGIN>
<p>(<a href="$TIDXFNAME$">go to $TIDXLABEL$</a>)</p>
<hr/>
<div style="text-align: left;">$PGLINK(PREV)$&nbsp;&nbsp;&nbsp;$PGLINK(NEXT)$</div>
<div style="text-align: center;">&nbsp;<a href="$PG(FIRST)$">&larr;</a>&nbsp;&nbsp;$PGLINKLIST(5;5)$&nbsp;&nbsp;<a href="$PG(LAST)$">&rarr;</a></div>
<ul>
</LISTBEGIN>

<LISTEND>
</ul>
<div style="text-align: center;">&nbsp;<a href="$PG(FIRST)$">&larr;</a>&nbsp;&nbsp;$PGLINKLIST(5;5)$&nbsp;&nbsp;<a href="$PG(LAST)$">&rarr;</a></div>
<div style="text-align: left;">$PGLINK(PREV)$&nbsp;&nbsp;&nbsp;$PGLINK(NEXT)$</div>
</LISTEND>

<!-- Formatting for the start of thread page.
     See http://www.mhonarc.org/MHonArc/doc/resources/thead.html. -->
<THEAD>
<p>(<a href="$IDXFNAME$">go to $IDXLABEL$</a>)</p>
<hr/>
<div style="text-align: left;">$PGLINK(TPREV)$&nbsp;&nbsp;&nbsp;$PGLINK(TNEXT)$</div>
<div style="text-align: center;">&nbsp;<a href="$PG(TFIRST)$">&larr;</a>&nbsp;&nbsp;$PGLINKLIST(T5;T5)$&nbsp;&nbsp;<a href="$PG(TLAST)$">&rarr;</a></div>
<ul>
</THEAD>

<TFOOT>
</ul>
<div style="text-align: center;">&nbsp;<a href="$PG(TFIRST)$">&larr;</a>&nbsp;&nbsp;$PGLINKLIST(T5;T5)$&nbsp;&nbsp;<a href="$PG(TLAST)$">&rarr;</a></div>
<div style="text-align: left;">$PGLINK(TPREV)$&nbsp;&nbsp;&nbsp;$PGLINK(TNEXT)$</div>
</TFOOT>

<!-- Per-message formatting on the indexed-by-date main page. -->
<LITEMPLATE>
<li><strong>$SUBJECT$</strong>
<ul><li><em>From</em>: $FROM$,&nbsp;<em>$YYYYMMDD$</em></li></ul>
</li>
</LITEMPLATE>

<!-- Per-message formatting on the thread page. -->
<TTOPBEGIN>
<li><strong>$SUBJECT$</strong>,
<em>$FROMNAME$, $YYYYMMDD$</em>
</TTOPBEGIN>
<TLITXT>
<li><strong>$SUBJECT$</strong>,
<em>$FROMNAME$, $YYYYMMDD$</em>
</TLITXT>
<TSINGLETXT>
<li><strong>$SUBJECT$</strong>,
<em>$FROMNAME$, $YYYYMMDD$</em>
</TSINGLETXT>

<!-- Modify appropriate resources to print our link at the bottom
     of MHonArc generated pages. Notice how the custom resource
     variable defined above can be used to include our link. -->

<!-- Main index pages -->
<IDXPGBEGIN>
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
        "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<title>$IDXTITLE$</title>
</head>
<body text="#000000" bgcolor="#FFFFFF">
<h1>$IDXTITLE$</h1>
</IDXPGBEGIN>
<IDXPGEND>
<hr/>
(<em>$ML-FULL-TITLE$, formatted by <a href="$DOCURL$">MHonArc</a>)
</body>
</html>
</IDXPGEND>

<!-- Thread index pages -->
<TIDXPGBEGIN>
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
        "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<title>$TIDXTITLE$</title>
</head>
<body text="#000000" bgcolor="#FFFFFF">
<h1>$TIDXTITLE$</h1>
</TIDXPGBEGIN>
<TIDXPGEND>
<hr/>
(<em>$ML-FULL-TITLE$, formatted by <a href="$DOCURL$">MHonArc</a>)
</body>
</html>
</TIDXPGEND>

<!-- Message pages -->
<MSGPGEND>
<hr/>
(<em>$ML-FULL-TITLE$, formatted by <a href="$DOCURL$">MHonArc</a>)
</body>
</html>
</MSGPGEND>
