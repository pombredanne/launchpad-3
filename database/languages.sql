-- arch-tag: 52b6712d-1ce0-4d61-83c5-b82f0e31596e
-- 
-- This script is ONLY valid/tested with new launchpad database
-- It's only a temporal hack until we automate the script execution
-- from launchpad/lib/canonical/rosetta/scripts/import_languages_and_countries.py
-- If you have any problem/doubt, just ask me:
-- Carlos Perelló Marín <carlos@interactors.coop>

COPY "language" (id, code, englishname, nativename) FROM stdin;
1	aa	Afar	\N
2	ab	Abkhazian	\N
3	ace	Achinese	\N
4	ach	Acoli	\N
5	ada	Adangme	\N
6	ady	Adyghe; Adygei	\N
7	afa	Afro-Asiatic (Other)	\N
8	afh	Afrihili	\N
9	af	Afrikaans	\N
10	aka	Akan	\N
11	ak	Akkadian	\N
12	sq	Albanian	\N
13	ale	Aleut	\N
14	alg	Algonquian languages	\N
15	am	Amharic	\N
16	ang	English, Old (ca.450-1100)	\N
17	apa	Apache languages	\N
18	ar	Arabic	\N
19	arc	Aramaic	\N
20	an	Aragonese	\N
21	hy	Armenian	\N
22	arn	Araucanian	\N
23	arp	Arapaho	\N
24	art	Artificial (Other)	\N
25	arw	Arawak	\N
26	as	Assamese	\N
27	ast	Asturian; Bable	\N
28	ath	Athapascan language	\N
29	aus	Australian languages	\N
30	av	Avaric	\N
31	ae	Avestan	\N
32	awa	Awadhi	\N
33	ay	Aymara	\N
34	az	Azerbaijani	\N
35	bad	Banda	\N
36	bai	Bamileke languages	\N
37	ba	Bashkir	\N
38	bal	Baluchi	\N
39	bm	Bambara	\N
40	ban	Balinese	\N
41	eu	Basque	\N
42	bas	Basa	\N
43	bat	Baltic (Other)	\N
44	bej	Beja	\N
45	be	Belarusian	\N
46	bem	Bemba	\N
47	bn	Bengali	\N
48	ber	Berber (Other)	\N
49	bho	Bhojpuri	\N
50	bh	Bihari	\N
51	bik	Bikol	\N
52	bin	Bini	\N
53	bi	Bislama	\N
54	bla	Siksika	\N
55	bnt	Bantu (Other)	\N
56	bs	Bosnian	\N
57	bra	Braj	\N
58	br	Breton	\N
59	btk	Batak (Indonesia)	\N
60	bua	Buriat	\N
61	bug	Buginese	\N
62	bg	Bulgarian	\N
63	my	Burmese	\N
64	byn	Blin; Bilin	\N
65	cad	Caddo	\N
66	cai	Central American Indian (Other)	\N
67	car	Carib	\N
68	ca	Catalan	\N
69	cau	Caucasian (Other)	\N
70	ceb	Cebuano	\N
71	cel	Celtic (Other)	\N
72	ch	Chamorro	\N
73	chb	Chibcha	\N
74	ce	Chechen	\N
75	chg	Chagatai	\N
76	zh	Chinese	\N
77	chk	Chukese	\N
78	chm	Mari	\N
79	chn	Chinook jargon	\N
80	cho	Choctaw	\N
81	chp	Chipewyan	\N
82	chr	Cherokee	\N
83	chu	Church Slavic	\N
84	cv	Chuvash	\N
85	chy	Cheyenne	\N
86	cmc	Chamic languages	\N
87	cop	Coptic	\N
88	kw	Cornish	\N
89	co	Corsican	\N
90	cpe	English-based (Other)	\N
91	cpf	French-based (Other)	\N
92	cpp	Portuguese-based (Other)	\N
93	cr	Cree	\N
94	crh	Crimean Turkish; Crimean Tatar	\N
95	crp	Creoles and pidgins (Other)	\N
96	csb	Kashubian	\N
97	cus	Cushitic (Other)	\N
98	cs	Czech	\N
99	dak	Dakota	\N
100	da	Danish	\N
101	dar	Dargwa	\N
102	del	Delaware	\N
103	den	Slave (Athapascan)	\N
104	dgr	Dogrib	\N
105	din	Dinka	\N
106	dv	Divehi	\N
107	doi	Dogri	\N
108	dra	Dravidian (Other)	\N
109	dsb	Lower Sorbian	\N
110	dua	Duala	\N
111	dum	Dutch, Middle (ca. 1050-1350)	\N
112	nl	Dutch	\N
113	dyu	Dyula	\N
114	dz	Dzongkha	\N
115	efi	Efik	\N
116	egy	Egyptian (Ancient)	\N
117	eka	Ekajuk	\N
118	elx	Elamite	\N
119	en	English	\N
120	enm	English, Middle (1100-1500)	\N
121	eo	Esperanto	\N
122	et	Estonian	\N
123	ee	Ewe	\N
124	ewo	Ewondo	\N
125	fan	Fang	\N
126	fo	Faroese	\N
127	fat	Fanti	\N
128	fj	Fijian	\N
129	fi	Finnish	\N
130	fiu	Finno-Ugrian (Other)	\N
131	fon	Fon	\N
132	fr	French	\N
133	frm	French, Middle (ca.1400-1600)	\N
134	fro	French, Old (842-ca.1400)	\N
135	fy	Frisian	\N
136	ff	Fulah	\N
137	fur	Friulian	\N
138	gaa	Ga	\N
139	gay	Gayo	\N
140	gba	Gbaya	\N
141	gem	Germanic (Other)	\N
142	ka	Georgian	\N
143	de	German	\N
144	gez	Geez	\N
145	gil	Gilbertese	\N
146	gd	Gaelic; Scottish	\N
147	ga	Irish	\N
148	gl	Gallegan	\N
149	gv	Manx	\N
150	gmh	German, Middle High (ca.1050-1500)	\N
151	goh	German, Old High (ca.750-1050)	\N
152	gon	Gondi	\N
153	gor	Gorontalo	\N
154	got	Gothic	\N
155	grb	Grebo	\N
156	grc	Greek, Ancient (to 1453)	\N
157	el	Greek, Modern (1453-)	\N
158	gn	Guarani	\N
159	gu	Gujarati	\N
160	gwi	Gwichin	\N
161	hai	Haida	\N
162	ht	Haitian; Haitian Creole	\N
163	ha	Hausa	\N
164	haw	Hawaiian	\N
165	he	Hebrew	\N
166	hz	Herero	\N
167	hil	Hiligaynon	\N
168	him	Himachali	\N
169	hi	Hindi	\N
170	hit	Hittite	\N
171	hmn	Hmong	\N
172	ho	Hiri	\N
173	hsb	Upper Sorbian	\N
174	hu	Hungarian	\N
175	hup	Hupa	\N
176	iba	Iban	\N
177	ig	Igbo	\N
178	is	Icelandic	\N
179	io	Ido	\N
180	ii	Sichuan Yi	\N
181	ijo	Ijo	\N
182	iu	Inuktitut	\N
183	ie	Interlingue	\N
184	ilo	Iloko	\N
185	ia	Interlingua	\N
186	inc	Indic (Other)	\N
187	id	Indonesian	\N
188	ine	Indo-European (Other)	\N
189	inh	Ingush	\N
190	ik	Inupiaq	\N
191	ira	Iranian (Other)	\N
192	iro	Iroquoian languages	\N
193	it	Italian	\N
194	jv	Javanese	\N
195	jbo	Lojban	\N
196	ja	Japanese	\N
197	jpr	Judeo-Persian	\N
198	jrb	Judeo-Arabic	\N
199	kaa	Kara-Kalpak	\N
200	kab	Kabyle	\N
201	kac	Kachin	\N
202	kl	Greenlandic (Kalaallisut)	\N
203	kam	Kamba	\N
204	kn	Kannada	\N
205	kar	Karen	\N
206	ks	Kashmiri	\N
207	kr	Kanuri	\N
208	kaw	Kawi	\N
209	kk	Kazakh	\N
210	kbd	Kabardian	\N
211	kha	Khazi	\N
212	khi	Khoisan (Other)	\N
213	km	Khmer	\N
214	kho	Khotanese	\N
215	ki	Kikuyu	\N
216	rw	Kinyarwanda	\N
217	ky	Kirghiz	\N
218	kmb	Kimbundu	\N
219	kok	Konkani	\N
220	kv	Komi	\N
221	kg	Kongo	\N
222	ko	Korean	\N
223	kos	Kosraean	\N
224	kpe	Kpelle	\N
225	krc	Karachay-Balkar	\N
226	kro	Kru	\N
227	kru	Kurukh	\N
228	kj	Kuanyama	\N
229	kum	Kumyk	\N
230	ku	Kurdish	\N
231	kut	Kutenai	\N
232	lad	Ladino	\N
233	lah	Lahnda	\N
234	lam	Lamba	\N
235	lo	Lao	\N
236	la	Latin	\N
237	lv	Latvian	\N
238	lez	Lezghian	\N
239	li	Limburgian	\N
240	ln	Lingala	\N
241	lt	Lithuanian	\N
242	lol	Mongo	\N
243	loz	Lozi	\N
244	lb	Luxembourgish	\N
245	lua	Luba-Lulua	\N
246	lu	Luba-Katanga	\N
247	lg	Ganda	\N
248	lui	Luiseno	\N
249	lun	Lunda	\N
250	luo	Luo (Kenya and Tanzania)	\N
251	lus	Lushai	\N
252	mk	Macedonian	\N
253	mad	Madurese	\N
254	mag	Magahi	\N
255	mh	Marshallese	\N
256	mai	Maithili	\N
257	mak	Makasar	\N
258	ml	Malayalam	\N
259	man	Mandingo	\N
260	mi	Maori	\N
261	map	Austronesian (Other)	\N
262	mr	Marathi	\N
263	mas	Masai	\N
264	ms	Malay	\N
265	mdf	Moksha	\N
266	mdr	Mandar	\N
267	men	Mende	\N
268	mga	Irish, Middle (900-1200)	\N
269	mic	Micmac	\N
270	min	Minangkabau	\N
271	mis	Miscellaneous languages	\N
272	mkh	Mon-Khmer (Other)	\N
273	mg	Malagasy	\N
274	mt	Maltese	\N
275	mnc	Manchu	\N
276	mno	Manobo languages	\N
277	moh	Mohawk	\N
278	mo	Moldavian	\N
279	mn	Mongolian	\N
280	mos	Mossi	\N
281	mul	Multiple languages	\N
282	mun	Munda languages	\N
283	mus	Creek	\N
284	mwr	Marwari	\N
285	myn	Mayan languages	\N
286	myv	Erzya	\N
287	nah	Nahuatl	\N
288	nai	North American Indian (Other)	\N
289	nap	Neapolitan	\N
290	na	Nauru	\N
291	nv	Navaho	\N
292	nr	Ndebele, South	\N
293	nd	Ndebele, North	\N
294	ng	Ndonga	\N
295	nds	German, Low	\N
296	ne	Nepali	\N
297	new	Newari	\N
298	nia	Nias	\N
299	nic	Niger-Kordofanian (Other)	\N
300	niu	Niuean	\N
301	nn	Norwegian Nynorsk	\N
302	nb	Bokmål, Norwegian	\N
303	nog	Nogai	\N
304	non	Norse, Old	\N
305	no	Norwegian	\N
306	nso	Sotho, Northern	\N
307	nub	Nubian languages	\N
308	nwc	Classical Newari; Old Newari	\N
309	ny	Chewa; Chichewa; Nyanja	\N
310	nym	Nyankole	\N
311	nyo	Nyoro	\N
312	nzi	Nzima	\N
313	oc	Occitan (post 1500)	\N
314	oj	Ojibwa	\N
315	or	Oriya	\N
316	om	Oromo	\N
317	osa	Osage	\N
318	os	Ossetian	\N
319	ota	Turkish, Ottoman (1500-1928)	\N
320	oto	Otomian languages	\N
321	paa	Papuan (Other)	\N
322	pag	Pangasinan	\N
323	pal	Pahlavi	\N
324	pam	Pampanga	\N
325	pa	Panjabi	\N
326	pap	Papiamento	\N
327	pau	Palauan	\N
328	peo	Persian, Old (ca.600-400 B.C.)	\N
329	fa	Persian	\N
330	phi	Philippine (Other)	\N
331	phn	Phoenician	\N
332	pi	Pali	\N
333	pl	Polish	\N
334	pt	Portuguese	\N
335	pon	Pohnpeian	\N
336	pra	Prakrit languages	\N
337	pro	Provençal, Old (to 1500)	\N
338	ps	Pushto	\N
339	qu	Quechua	\N
340	raj	Rajasthani	\N
341	rap	Rapanui	\N
342	rar	Rarotongan	\N
343	roa	Romance (Other)	\N
344	rm	Raeto-Romance	\N
345	rom	Romany	\N
346	ro	Romanian	\N
347	rn	Rundi	\N
348	ru	Russian	\N
349	sad	Sandawe	\N
350	sg	Sango	\N
351	sah	Yakut	\N
352	sai	South American Indian (Other)	\N
353	sal	Salishan languages	\N
354	sam	Samaritan Aramaic	\N
355	sa	Sanskrit	\N
356	sas	Sasak	\N
357	sat	Santali	\N
358	sr	Serbian	\N
359	sco	Scots	\N
360	hr	Croatian	\N
361	sel	Selkup	\N
362	sem	Semitic (Other)	\N
363	sga	Irish, Old (to 900)	\N
364	sgn	Sign languages	\N
365	shn	Shan	\N
366	sid	Sidamo	\N
367	si	Sinhalese	\N
368	sio	Siouan languages	\N
369	sit	Sino-Tibetan (Other)	\N
370	sla	Slavic (Other)	\N
371	sk	Slovak	\N
372	sl	Slovenian	\N
373	sma	Southern Sami	\N
374	se	Northern Sami	\N
375	smi	Sami languages (Other)	\N
376	smj	Lule Sami	\N
377	smn	Inari Sami	\N
378	sm	Samoan	\N
379	sms	Skolt Sami	\N
380	sn	Shona	\N
381	sd	Sindhi	\N
382	snk	Soninke	\N
383	sog	Sogdian	\N
384	so	Somali	\N
385	son	Songhai	\N
386	st	Sotho, Southern	\N
387	es	Spanish (Castilian)	\N
388	sc	Sardinian	\N
389	srr	Serer	\N
390	ssa	Nilo-Saharan (Other)	\N
391	ss	Swati	\N
392	suk	Sukuma	\N
393	su	Sundanese	\N
394	sus	Susu	\N
395	sux	Sumerian	\N
396	sw	Swahili	\N
397	sv	Swedish	\N
398	syr	Syriac	\N
399	ty	Tahitian	\N
400	tai	Tai (Other)	\N
401	ta	Tamil	\N
402	ts	Tsonga	\N
403	tt	Tatar	\N
404	te	Telugu	\N
405	tem	Timne	\N
406	ter	Tereno	\N
407	tet	Tetum	\N
408	tg	Tajik	\N
409	tl	Tagalog	\N
410	th	Thai	\N
411	bo	Tibetan	\N
412	tig	Tigre	\N
413	ti	Tigrinya	\N
414	tiv	Tiv	\N
415	tlh	Klingon; tlhIngan-Hol	\N
416	tkl	Tokelau	\N
417	tli	Tlinglit	\N
418	tmh	Tamashek	\N
419	tog	Tonga (Nyasa)	\N
420	to	Tonga (Tonga Islands)	\N
421	tpi	Tok Pisin	\N
422	tsi	Tsimshian	\N
423	tn	Tswana	\N
424	tk	Turkmen	\N
425	tum	Tumbuka	\N
426	tup	Tupi languages	\N
427	tr	Turkish	\N
428	tut	Altaic (Other)	\N
429	tvl	Tuvalu	\N
430	tw	Twi	\N
431	tyv	Tuvinian	\N
432	udm	Udmurt	\N
433	uga	Ugaritic	\N
434	ug	Uighur	\N
435	uk	Ukrainian	\N
436	umb	Umbundu	\N
437	und	Undetermined	\N
438	urd	Urdu	\N
439	uz	Uzbek	\N
440	vai	Vai	\N
441	ve	Venda	\N
442	vi	Vietnamese	\N
443	vo	Volapuk	\N
444	vot	Votic	\N
445	wak	Wakashan languages	\N
446	wal	Walamo	\N
447	war	Waray	\N
448	was	Washo	\N
449	cy	Welsh	\N
450	wen	Sorbian languages	\N
451	wa	Walloon	\N
452	wo	Wolof	\N
453	xal	Kalmyk	\N
454	xh	Xhosa	\N
455	yao	Yao	\N
456	yap	Yapese	\N
457	yi	Yiddish	\N
458	yo	Yoruba	\N
459	ypk	Yupik languages	\N
460	zap	Zapotec	\N
461	zen	Zenaga	\N
462	za	Chuang; Zhuang	\N
463	znd	Zande	\N
464	zu	Zulu	\N
465	zun	Zuni	\N
466	ro_RO	Romanian from Romania	\N
467	ar_TN	Arabic from Tunisia	\N
468	pa_IN	Panjabi from India	\N
469	ar_MA	Arabic from Morocco	\N
470	ar_LY	Arabic from Libyan Arab Jamahiriya	\N
471	es_SV	Spanish (Castilian) from El Salvador	\N
472	ga_IE	Irish from Ireland	\N
473	ta_IN	Tamil from India	\N
474	en_HK	English from Hong Kong	\N
475	cs_CZ	Czech from Czech Republic	\N
476	ar_LB	Arabic from Lebanon	\N
477	it_IT	Italian from Italy	\N
478	es_CO	Spanish (Castilian) from Colombia	\N
479	ti_ET	Tigrinya from Ethiopia	\N
480	ar_DZ	Arabic from Algeria	\N
481	de_BE	German from Belgium	\N
482	mk_MK	Macedonian from Macedonia, the Former Yugoslav Republic of	\N
483	gv_GB	Manx from United Kingdom	\N
484	th_TH	Thai from Thailand	\N
485	uz_UZ	Uzbek from Uzbekistan	\N
486	bn_IN	Bengali from India	\N
487	tl_PH	Tagalog from Philippines	\N
488	en_PH	English from Philippines	\N
489	mi_NZ	Maori from New Zealand	\N
490	pl_PL	Polish from Poland	\N
491	ar_YE	Arabic from Yemen	\N
492	az_AZ	Azerbaijani from Azerbaijan	\N
493	es_NI	Spanish (Castilian) from Nicaragua	\N
494	af_ZA	Afrikaans from South Africa	\N
495	ar_QA	Arabic from Qatar	\N
496	kl_GL	Greenlandic (Kalaallisut) from Greenland	\N
497	en_ZA	English from South Africa	\N
498	ja_JP	Japanese from Japan	\N
499	zh_HK	Chinese from Hong Kong	\N
500	en_ZW	English from Zimbabwe	\N
501	so_ET	Somali from Ethiopia	\N
502	lv_LV	Latvian from Latvia	\N
503	tt_RU	Tatar from Russian Federation	\N
504	aa_ET	Afar from Ethiopia	\N
505	ar_IN	Arabic from India	\N
506	aa_ER	Afar from Eritrea	\N
507	se_NO	Northern Sami from Norway	\N
508	en_US	English from United States	\N
509	ar_AE	Arabic from United Arab Emirates	\N
510	mt_MT	Maltese from Malta	\N
511	om_KE	Oromo from Kenya	\N
512	ar_IQ	Arabic from Iraq	\N
513	fr_BE	French from Belgium	\N
514	pt_BR	Portuguese from Brazil	\N
515	es_PR	Spanish (Castilian) from Puerto Rico	\N
516	gu_IN	Gujarati from India	\N
517	sid_ET	Sidamo from Ethiopia	\N
518	wa_BE	Walloon from Belgium	\N
519	oc_FR	Occitan (post 1500) from France	\N
520	en_BW	English from Botswana	\N
521	om_ET	Oromo from Ethiopia	\N
522	hi_IN	Hindi from India	\N
523	es_VE	Spanish (Castilian) from Venezuela	\N
524	an_ES	Aragonese from Spain	\N
525	it_CH	Italian from Switzerland	\N
526	da_DK	Danish from Denmark	\N
527	es_AR	Spanish (Castilian) from Argentina	\N
528	ne_NP	Nepali from Nepal	\N
529	sq_AL	Albanian from Albania	\N
530	hu_HU	Hungarian from Hungary	\N
531	sk_SK	Slovak from Slovakia	\N
532	mn_MN	Mongolian from Mongolia	\N
533	ar_KW	Arabic from Kuwait	\N
534	ar_SA	Arabic from Saudi Arabia	\N
535	ar_SD	Arabic from Sudan	\N
536	pt_PT	Portuguese from Portugal	\N
537	nn_NO	Norwegian Nynorsk from Norway	\N
538	ar_SY	Arabic from Syrian Arab Republic	\N
539	byn_ER	Blin; Bilin from Eritrea	\N
540	en_GB	English from United Kingdom	\N
541	et_EE	Estonian from Estonia	\N
542	lt_LT	Lithuanian from Lithuania	\N
543	zu_ZA	Zulu from South Africa	\N
544	zh_SG	Chinese from Singapore	\N
545	es_DO	Spanish (Castilian) from Dominican Republic	\N
546	lg_UG	Ganda from Uganda	\N
547	id_ID	Indonesian from Indonesia	\N
548	hr_HR	Croatian from Croatia	\N
549	es_CL	Spanish (Castilian) from Chile	\N
550	sl_SI	Slovenian from Slovenia	\N
551	is_IS	Icelandic from Iceland	\N
552	gez_ER	Geez from Eritrea	\N
553	fo_FO	Faroese from Faroe Islands	\N
554	bs_BA	Bosnian from Bosnia and Herzegovina	\N
555	ti_ER	Tigrinya from Eritrea	\N
556	en_DK	English from Denmark	\N
557	no_NO	Norwegian from Norway	\N
558	eu_ES	Basque from Spain	\N
559	kw_GB	Cornish from United Kingdom	\N
560	ms_MY	Malay from Malaysia	\N
561	kn_IN	Kannada from India	\N
562	es_GT	Spanish (Castilian) from Guatemala	\N
563	be_BY	Belarusian from Belarus	\N
564	vi_VN	Vietnamese from Viet Nam	\N
565	fr_CA	French from Canada	\N
566	aa_DJ	Afar from Djibouti	\N
567	fr_CH	French from Switzerland	\N
568	fi_FI	Finnish from Finland	\N
569	so_DJ	Somali from Djibouti	\N
570	en_IN	English from India	\N
571	en_AU	English from Australia	\N
572	en_IE	English from Ireland	\N
573	tr_TR	Turkish from Turkey	\N
574	bn_BD	Bengali from Bangladesh	\N
575	ru_UA	Russian from Ukraine	\N
576	gd_GB	Gaelic; Scottish from United Kingdom	\N
577	nl_BE	Dutch from Belgium	\N
578	de_CH	German from Switzerland	\N
579	es_BO	Spanish (Castilian) from Bolivia	\N
580	te_IN	Telugu from India	\N
581	zh_TW	Chinese from Taiwan, Province of China	\N
582	xh_ZA	Xhosa from South Africa	\N
583	es_CR	Spanish (Castilian) from Costa Rica	\N
584	am_ET	Amharic from Ethiopia	\N
585	gez_ET	Geez from Ethiopia	\N
586	ar_EG	Arabic from Egypt	\N
587	ca_ES	Catalan from Spain	\N
588	fr_FR	French from France	\N
589	zh_CN	Chinese from China	\N
590	es_UY	Spanish (Castilian) from Uruguay	\N
591	tg_TJ	Tajik from Tajikistan	\N
592	nl_NL	Dutch from Netherlands	\N
593	es_US	Spanish (Castilian) from United States	\N
594	yi_US	Yiddish from United States	\N
595	ml_IN	Malayalam from India	\N
596	uk_UA	Ukrainian from Ukraine	\N
597	de_LU	German from Luxembourg	\N
598	st_ZA	Sotho, Southern from South Africa	\N
599	es_MX	Spanish (Castilian) from Mexico	\N
600	ar_JO	Arabic from Jordan	\N
601	fa_IR	Persian from Iran, Islamic Republic of	\N
602	lo_LA	Lao from Lao People's Democratic Republic	\N
603	es_EC	Spanish (Castilian) from Ecuador	\N
604	so_KE	Somali from Kenya	\N
605	en_NZ	English from New Zealand	\N
606	he_IL	Hebrew from Israel	\N
607	sv_SE	Swedish from Sweden	\N
608	ru_RU	Russian from Russian Federation	\N
609	cy_GB	Welsh from United Kingdom	\N
610	br_FR	Breton from France	\N
611	el_GR	Greek, Modern (1453-) from Greece	\N
612	es_ES	Spanish (Castilian) from Spain	\N
613	ar_BH	Arabic from Bahrain	\N
614	bg_BG	Bulgarian from Bulgaria	\N
615	de_DE	German from Germany	\N
616	gl_ES	Gallegan from Spain	\N
617	mr_IN	Marathi from India	\N
618	en_CA	English from Canada	\N
619	es_PY	Spanish (Castilian) from Paraguay	\N
620	so_SO	Somali from Somalia	\N
621	fr_LU	French from Luxembourg	\N
622	ar_OM	Arabic from Oman	\N
623	es_PA	Spanish (Castilian) from Panama	\N
624	sv_FI	Swedish from Finland	\N
625	ka_GE	Georgian from Georgia	\N
626	es_PE	Spanish (Castilian) from Peru	\N
627	nb_NO	Bokmål, Norwegian from Norway	\N
628	tig_ER	Tigre from Eritrea	\N
629	es_HN	Spanish (Castilian) from Honduras	\N
630	ko_KR	Korean from Korea, Republic of	\N
631	de_AT	German from Austria	\N
632	en_SG	English from Singapore	\N
\.

SELECT pg_catalog.setval('language_id_seq', 632, true);

COPY country (id, iso3166code2, iso3166code3, name, title, description) FROM stdin;
1	AF	AFG	Afghanistan	The Transitional Islamic State of Afghanistan	\N
2	AX	ALA	Åland Islands	\N	\N
3	AL	ALB	Albania	Republic of Albania	\N
4	DZ	DZA	Algeria	People's Democratic Republic of Algeria	\N
5	AS	ASM	American Samoa	\N	\N
6	AD	AND	Andorra	Principality of Andorra	\N
7	AO	AGO	Angola	Republic of Angola	\N
8	AI	AIA	Anguilla	\N	\N
9	AQ	ATA	Antarctica	\N	\N
10	AG	ATG	Antigua and Barbuda	\N	\N
11	AR	ARG	Argentina	Argentine Republic	\N
12	AM	ARM	Armenia	Republic of Armenia	\N
13	AW	ABW	Aruba	\N	\N
14	AU	AUS	Australia	\N	\N
15	AT	AUT	Austria	Republic of Austria	\N
16	AZ	AZE	Azerbaijan	Republic of Azerbaijan	\N
17	BS	BHS	Bahamas	Commonwealth of the Bahamas	\N
18	BH	BHR	Bahrain	State of Bahrain	\N
19	BD	BGD	Bangladesh	People's Republic of Bangladesh	\N
20	BB	BRB	Barbados	\N	\N
21	BY	BLR	Belarus	Republic of Belarus	\N
22	BE	BEL	Belgium	Kingdom of Belgium	\N
23	BZ	BLZ	Belize	\N	\N
24	BJ	BEN	Benin	Republic of Benin	\N
25	BM	BMU	Bermuda	\N	\N
26	BT	BTN	Bhutan	Kingdom of Bhutan	\N
27	BO	BOL	Bolivia	Republic of Bolivia	\N
28	BA	BIH	Bosnia and Herzegovina	Republic of Bosnia and Herzegovina	\N
29	BW	BWA	Botswana	Republic of Botswana	\N
30	BV	BVT	Bouvet Island	\N	\N
31	BR	BRA	Brazil	Federative Republic of Brazil	\N
32	IO	IOT	British Indian Ocean Territory	\N	\N
33	BN	BRN	Brunei Darussalam	\N	\N
34	BG	BGR	Bulgaria	Republic of Bulgaria	\N
35	BF	BFA	Burkina Faso	\N	\N
36	BI	BDI	Burundi	Republic of Burundi	\N
37	KH	KHM	Cambodia	Kingdom of Cambodia	\N
38	CM	CMR	Cameroon	Republic of Cameroon	\N
39	CA	CAN	Canada	\N	\N
40	CV	CPV	Cape Verde	Republic of Cape Verde	\N
41	KY	CYM	Cayman Islands	\N	\N
42	CF	CAF	Central African Republic	\N	\N
43	TD	TCD	Chad	Republic of Chad	\N
44	CL	CHL	Chile	Republic of Chile	\N
45	CN	CHN	China	People's Republic of China	\N
46	CX	CXR	Christmas Island	\N	\N
47	CC	CCK	Cocos (Keeling) Islands	\N	\N
48	CO	COL	Colombia	Republic of Colombia	\N
49	KM	COM	Comoros	Union of the Comoros	\N
50	CG	COG	Congo	Republic of the Congo	\N
51	CD	ZAR	Congo, The Democratic Republic of the	\N	\N
52	CK	COK	Cook Islands	\N	\N
53	CR	CRI	Costa Rica	Republic of Costa Rica	\N
54	CI	CIV	Côte d'Ivoire	Republic of Cote d'Ivoire	\N
55	HR	HRV	Croatia	Republic of Croatia	\N
56	CU	CUB	Cuba	Republic of Cuba	\N
57	CY	CYP	Cyprus	Republic of Cyprus	\N
58	CZ	CZE	Czech Republic	\N	\N
59	DK	DNK	Denmark	Kingdom of Denmark	\N
60	DJ	DJI	Djibouti	Republic of Djibouti	\N
61	DM	DMA	Dominica	Commonwealth of Dominica	\N
62	DO	DOM	Dominican Republic	\N	\N
63	TL	TLS	Timor-Leste	Democratic Republic of Timor-Leste	\N
64	EC	ECU	Ecuador	Republic of Ecuador	\N
65	EG	EGY	Egypt	Arab Republic of Egypt	\N
66	SV	SLV	El Salvador	Republic of El Salvador	\N
67	GQ	GNQ	Equatorial Guinea	Republic of Equatorial Guinea	\N
68	ER	ERI	Eritrea	\N	\N
69	EE	EST	Estonia	Republic of Estonia	\N
70	ET	ETH	Ethiopia	Federal Democratic Republic of Ethiopia	\N
71	FK	FLK	Falkland Islands (Malvinas)	\N	\N
72	FO	FRO	Faroe Islands	\N	\N
73	FJ	FJI	Fiji	Republic of the Fiji Islands	\N
74	FI	FIN	Finland	Republic of Finland	\N
75	FR	FRA	France	French Republic	\N
76	GF	GUF	French Guiana	\N	\N
77	PF	PYF	French Polynesia	\N	\N
78	TF	ATF	French Southern Territories	\N	\N
79	GA	GAB	Gabon	Gabonese Republic	\N
80	GM	GMB	Gambia	Republic of the Gambia	\N
81	GE	GEO	Georgia	\N	\N
82	DE	DEU	Germany	Federal Republic of Germany	\N
83	GH	GHA	Ghana	Republic of Ghana	\N
84	GI	GIB	Gibraltar	\N	\N
85	GR	GRC	Greece	Hellenic Republic	\N
86	GL	GRL	Greenland	\N	\N
87	GD	GRD	Grenada	\N	\N
88	GP	GLP	Guadeloupe	\N	\N
89	GU	GUM	Guam	\N	\N
90	GT	GTM	Guatemala	Republic of Guatemala	\N
91	GN	GIN	Guinea	Republic of Guinea	\N
92	GW	GNB	Guinea-Bissau	Republic of Guinea-Bissau	\N
93	GY	GUY	Guyana	Republic of Guyana	\N
94	HT	HTI	Haiti	Republic of Haiti	\N
95	HM	HMD	Heard Island and McDonald Islands	\N	\N
96	VA	VAT	Holy See (Vatican City State)	\N	\N
97	HN	HND	Honduras	Republic of Honduras	\N
98	HK	HKG	Hong Kong	Hong Kong Special Administrative Region of China	\N
99	HU	HUN	Hungary	Republic of Hungary	\N
100	IS	ISL	Iceland	Republic of Iceland	\N
101	IN	IND	India	Republic of India	\N
102	ID	IDN	Indonesia	Republic of Indonesia	\N
103	IR	IRN	Iran, Islamic Republic of	Islamic Republic of Iran	\N
104	IQ	IRQ	Iraq	Republic of Iraq	\N
105	IE	IRL	Ireland	\N	\N
106	IL	ISR	Israel	State of Israel	\N
107	IT	ITA	Italy	Italian Republic	\N
108	JM	JAM	Jamaica	\N	\N
109	JP	JPN	Japan	\N	\N
110	JO	JOR	Jordan	Hashemite Kingdom of Jordan	\N
111	KZ	KAZ	Kazakhstan	Republic of Kazakhstan	\N
112	KE	KEN	Kenya	Republic of Kenya	\N
113	KI	KIR	Kiribati	Republic of Kiribati	\N
114	KP	PRK	Korea, Democratic People's Republic of	Democratic People's Republic of Korea	\N
115	KR	KOR	Korea, Republic of	\N	\N
116	KW	KWT	Kuwait	State of Kuwait	\N
117	KG	KGZ	Kyrgyzstan	Kyrgyz Republic	\N
118	LA	LAO	Lao People's Democratic Republic	\N	\N
119	LV	LVA	Latvia	Republic of Latvia	\N
120	LB	LBN	Lebanon	Lebanese Republic	\N
121	LS	LSO	Lesotho	Kingdom of Lesotho	\N
122	LR	LBR	Liberia	Republic of Liberia	\N
123	LY	LBY	Libyan Arab Jamahiriya	Socialist People's Libyan Arab Jamahiriya	\N
124	LI	LIE	Liechtenstein	Principality of Liechtenstein	\N
125	LT	LTU	Lithuania	Republic of Lithuania	\N
126	LU	LUX	Luxembourg	Grand Duchy of Luxembourg	\N
127	MO	MAC	Macao	Macao Special Administrative Region of China	\N
128	MK	MKD	Macedonia, the Former Yugoslav Republic of	The Former Yugoslav Republic of Macedonia	\N
129	MG	MDG	Madagascar	Republic of Madagascar	\N
130	MW	MWI	Malawi	Republic of Malawi	\N
131	MY	MYS	Malaysia	\N	\N
132	MV	MDV	Maldives	Republic of Maldives	\N
133	ML	MLI	Mali	Republic of Mali	\N
134	MT	MLT	Malta	Republic of Malta	\N
135	MH	MHL	Marshall Islands	Republic of the Marshall Islands	\N
136	MQ	MTQ	Martinique	\N	\N
137	MR	MRT	Mauritania	Islamic Republic of Mauritania	\N
138	MU	MUS	Mauritius	Republic of Mauritius	\N
139	YT	MYT	Mayotte	\N	\N
140	MX	MEX	Mexico	United Mexican States	\N
141	FM	FSM	Micronesia, Federated States of	Federated States of Micronesia	\N
142	MD	MDA	Moldova, Republic of	Republic of Moldova	\N
143	MC	MCO	Monaco	Principality of Monaco	\N
144	MN	MNG	Mongolia	\N	\N
145	MS	MSR	Montserrat	\N	\N
146	MA	MAR	Morocco	Kingdom of Morocco	\N
147	MZ	MOZ	Mozambique	Republic of Mozambique	\N
148	MM	MMR	Myanmar	Union of Myanmar	\N
149	NA	NAM	Namibia	Republic of Namibia	\N
150	NR	NRU	Nauru	Republic of Nauru	\N
151	NP	NPL	Nepal	Kingdom of Nepal	\N
152	NL	NLD	Netherlands	Kingdom of the Netherlands	\N
153	AN	ANT	Netherlands Antilles	\N	\N
154	NC	NCL	New Caledonia	\N	\N
155	NZ	NZL	New Zealand	\N	\N
156	NI	NIC	Nicaragua	Republic of Nicaragua	\N
157	NE	NER	Niger	Republic of the Niger	\N
158	NG	NGA	Nigeria	Federal Republic of Nigeria	\N
159	NU	NIU	Niue	Republic of Niue	\N
160	NF	NFK	Norfolk Island	\N	\N
161	MP	MNP	Northern Mariana Islands	Commonwealth of the Northern Mariana Islands	\N
162	NO	NOR	Norway	Kingdom of Norway	\N
163	OM	OMN	Oman	Sultanate of Oman	\N
164	PK	PAK	Pakistan	Islamic Republic of Pakistan	\N
165	PW	PLW	Palau	Republic of Palau	\N
166	PS	PSE	Palestinian Territory, Occupied	Occupied Palestinian Territory	\N
167	PA	PAN	Panama	Republic of Panama	\N
168	PG	PNG	Papua New Guinea	\N	\N
169	PY	PRY	Paraguay	Republic of Paraguay	\N
170	PE	PER	Peru	Republic of Peru	\N
171	PH	PHL	Philippines	Republic of the Philippines	\N
172	PN	PCN	Pitcairn	\N	\N
173	PL	POL	Poland	Republic of Poland	\N
174	PT	PRT	Portugal	Portuguese Republic	\N
175	PR	PRI	Puerto Rico	\N	\N
176	QA	QAT	Qatar	State of Qatar	\N
177	RE	REU	Reunion	\N	\N
178	RO	ROU	Romania	\N	\N
179	RU	RUS	Russian Federation	\N	\N
180	RW	RWA	Rwanda	Rwandese Republic	\N
181	SH	SHN	Saint Helena	\N	\N
182	KN	KNA	Saint Kitts and Nevis	\N	\N
183	LC	LCA	Saint Lucia	\N	\N
184	PM	SPM	Saint Pierre and Miquelon	\N	\N
185	VC	VCT	Saint Vincent and the Grenadines	\N	\N
186	WS	WSM	Samoa	Independent State of Samoa	\N
187	SM	SMR	San Marino	Republic of San Marino	\N
188	ST	STP	Sao Tome and Principe	Democratic Republic of Sao Tome and Principe	\N
189	SA	SAU	Saudi Arabia	Kingdom of Saudi Arabia	\N
190	SN	SEN	Senegal	Republic of Senegal	\N
191	SC	SYC	Seychelles	Republic of Seychelles	\N
192	SL	SLE	Sierra Leone	Republic of Sierra Leone	\N
193	SG	SGP	Singapore	Republic of Singapore	\N
194	SK	SVK	Slovakia	Slovak Republic	\N
195	SI	SVN	Slovenia	Republic of Slovenia	\N
196	SB	SLB	Solomon Islands	\N	\N
197	SO	SOM	Somalia	Somali Republic	\N
198	ZA	ZAF	South Africa	Republic of South Africa	\N
199	GS	SGS	South Georgia and the South Sandwich Islands	\N	\N
200	ES	ESP	Spain	Kingdom of Spain	\N
201	LK	LKA	Sri Lanka	Democratic Socialist Republic of Sri Lanka	\N
202	SD	SDN	Sudan	Republic of the Sudan	\N
203	SR	SUR	Suriname	Republic of Suriname	\N
204	SJ	SJM	Svalbard and Jan Mayen	\N	\N
205	SZ	SWZ	Swaziland	Kingdom of Swaziland	\N
206	SE	SWE	Sweden	Kingdom of Sweden	\N
207	CH	CHE	Switzerland	Swiss Confederation	\N
208	SY	SYR	Syrian Arab Republic	\N	\N
209	TW	TWN	Taiwan, Province of China	Taiwan, Province of China	\N
210	TJ	TJK	Tajikistan	Republic of Tajikistan	\N
211	TZ	TZA	Tanzania, United Republic of	United Republic of Tanzania	\N
212	TH	THA	Thailand	Kingdom of Thailand	\N
213	TG	TGO	Togo	Togolese Republic	\N
214	TK	TKL	Tokelau	\N	\N
215	TO	TON	Tonga	Kingdom of Tonga	\N
216	TT	TTO	Trinidad and Tobago	Republic of Trinidad and Tobago	\N
217	TN	TUN	Tunisia	Republic of Tunisia	\N
218	TR	TUR	Turkey	Republic of Turkey	\N
219	TM	TKM	Turkmenistan	\N	\N
220	TC	TCA	Turks and Caicos Islands	\N	\N
221	TV	TUV	Tuvalu	\N	\N
222	UG	UGA	Uganda	Republic of Uganda	\N
223	UA	UKR	Ukraine	\N	\N
224	AE	ARE	United Arab Emirates	\N	\N
225	GB	GBR	United Kingdom	United Kingdom of Great Britain and Northern Ireland	\N
226	US	USA	United States	United States of America	\N
227	UM	UMI	United States Minor Outlying Islands	\N	\N
228	UY	URY	Uruguay	Eastern Republic of Uruguay	\N
229	UZ	UZB	Uzbekistan	Republic of Uzbekistan	\N
230	VU	VUT	Vanuatu	Republic of Vanuatu	\N
231	VE	VEN	Venezuela	Bolivarian Republic of Venezuela	\N
232	VN	VNM	Viet Nam	Socialist Republic of Viet Nam	\N
233	VG	VGB	Virgin Islands, British	British Virgin Islands	\N
234	VI	VIR	Virgin Islands, U.S.	Virgin Islands of the United States	\N
235	WF	WLF	Wallis and Futuna	\N	\N
236	EH	ESH	Western Sahara	\N	\N
237	YE	YEM	Yemen	Republic of Yemen	\N
238	ZM	ZMB	Zambia	Republic of Zambia	\N
239	ZW	ZWE	Zimbabwe	Republic of Zimbabwe	\N
240	CS	SCG	Serbia and Montenegro	\N	\N
\.

SELECT pg_catalog.setval('country_id_seq', 240, true);

COPY spokenin ("language", country) FROM stdin;
346	178
466	178
18	217
467	217
325	101
468	101
18	146
469	146
18	123
470	123
387	66
471	66
147	105
472	105
401	101
473	101
119	98
474	98
98	58
475	58
18	120
476	120
193	107
477	107
387	48
478	48
413	70
479	70
18	4
480	4
143	22
481	22
252	128
482	128
149	225
483	225
410	212
484	212
439	229
485	229
47	101
486	101
409	171
487	171
119	171
488	171
260	155
489	155
333	173
490	173
18	237
491	237
34	16
492	16
387	156
493	156
9	198
494	198
18	176
495	176
202	86
496	86
119	198
497	198
196	109
498	109
76	98
499	98
119	239
500	239
384	70
501	70
237	119
502	119
403	179
503	179
1	70
504	70
18	101
505	101
1	68
506	68
374	162
507	162
119	226
508	226
18	224
509	224
274	134
510	134
316	112
511	112
18	104
512	104
132	22
513	22
334	31
514	31
387	175
515	175
159	101
516	101
366	70
517	70
451	22
518	22
313	75
519	75
119	29
520	29
316	70
521	70
169	101
522	101
387	231
523	231
20	200
524	200
193	207
525	207
100	59
526	59
387	11
527	11
296	151
528	151
12	3
529	3
174	99
530	99
371	194
531	194
279	144
532	144
18	116
533	116
18	189
534	189
18	202
535	202
334	174
536	174
301	162
537	162
18	208
538	208
64	68
539	68
119	225
540	225
122	69
541	69
241	125
542	125
464	198
543	198
76	193
544	193
387	62
545	62
247	222
546	222
187	102
547	102
360	55
548	55
387	44
549	44
372	195
550	195
178	100
551	100
144	68
552	68
126	72
553	72
56	28
554	28
413	68
555	68
119	59
556	59
305	162
557	162
41	200
558	200
88	225
559	225
264	131
560	131
204	101
561	101
387	90
562	90
45	21
563	21
442	232
564	232
132	39
565	39
1	60
566	60
132	207
567	207
129	74
568	74
384	60
569	60
119	101
570	101
119	14
571	14
119	105
572	105
427	218
573	218
47	19
574	19
348	223
575	223
146	225
576	225
112	22
577	22
143	207
578	207
387	27
579	27
404	101
580	101
76	209
581	209
454	198
582	198
387	53
583	53
15	70
584	70
144	70
585	70
18	65
586	65
68	200
587	200
132	75
588	75
76	45
589	45
387	228
590	228
408	210
591	210
112	152
592	152
387	226
593	226
457	226
594	226
258	101
595	101
435	223
596	223
143	126
597	126
386	198
598	198
387	140
599	140
18	110
600	110
329	103
601	103
235	118
602	118
387	64
603	64
384	112
604	112
119	155
605	155
165	106
606	106
397	206
607	206
348	179
608	179
449	225
609	225
58	75
610	75
157	85
611	85
387	200
612	200
18	18
613	18
62	34
614	34
143	82
615	82
148	200
616	200
262	101
617	101
119	39
618	39
387	169
619	169
384	197
620	197
132	126
621	126
18	163
622	163
387	167
623	167
397	74
624	74
142	81
625	81
387	170
626	170
302	162
627	162
412	68
628	68
387	97
629	97
222	115
630	115
143	15
631	15
119	193
632	193
\.


