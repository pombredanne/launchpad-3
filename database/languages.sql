-- arch-tag: 52b6712d-1ce0-4d61-83c5-b82f0e31596e
-- 
-- This script is ONLY valid/tested with new launchpad database
-- It's only a temporal hack until we automate the script execution
-- from launchpad/lib/canonical/rosetta/scripts/import_languages_and_countries.py
-- If you have any problem/doubt, just ask me:
-- Carlos Perelló Marín <carlos@interactors.coop>

COPY "language" (id, code, englishname, nativename, pluralforms, pluralexpression) FROM stdin;
1	aa	Afar	\N	\N	\N
2	ab	Abkhazian	\N	\N	\N
3	ace	Achinese	\N	\N	\N
4	ach	Acoli	\N	\N	\N
5	ada	Adangme	\N	\N	\N
6	ady	Adyghe; Adygei	\N	\N	\N
7	afa	Afro-Asiatic (Other)	\N	\N	\N
8	afh	Afrihili	\N	\N	\N
10	aka	Akan	\N	\N	\N
11	ak	Akkadian	\N	\N	\N
12	sq	Albanian	\N	\N	\N
13	ale	Aleut	\N	\N	\N
14	alg	Algonquian languages	\N	\N	\N
15	am	Amharic	\N	\N	\N
16	ang	English, Old (ca.450-1100)	\N	\N	\N
17	apa	Apache languages	\N	\N	\N
19	arc	Aramaic	\N	\N	\N
20	an	Aragonese	\N	\N	\N
21	hy	Armenian	\N	\N	\N
22	arn	Araucanian	\N	\N	\N
23	arp	Arapaho	\N	\N	\N
24	art	Artificial (Other)	\N	\N	\N
25	arw	Arawak	\N	\N	\N
26	as	Assamese	\N	\N	\N
27	ast	Asturian; Bable	\N	\N	\N
28	ath	Athapascan language	\N	\N	\N
29	aus	Australian languages	\N	\N	\N
30	av	Avaric	\N	\N	\N
31	ae	Avestan	\N	\N	\N
32	awa	Awadhi	\N	\N	\N
33	ay	Aymara	\N	\N	\N
35	bad	Banda	\N	\N	\N
36	bai	Bamileke languages	\N	\N	\N
37	ba	Bashkir	\N	\N	\N
38	bal	Baluchi	\N	\N	\N
39	bm	Bambara	\N	\N	\N
40	ban	Balinese	\N	\N	\N
42	bas	Basa	\N	\N	\N
43	bat	Baltic (Other)	\N	\N	\N
44	bej	Beja	\N	\N	\N
45	be	Belarusian	\N	\N	\N
46	bem	Bemba	\N	\N	\N
47	bn	Bengali	\N	\N	\N
48	ber	Berber (Other)	\N	\N	\N
49	bho	Bhojpuri	\N	\N	\N
50	bh	Bihari	\N	\N	\N
51	bik	Bikol	\N	\N	\N
52	bin	Bini	\N	\N	\N
53	bi	Bislama	\N	\N	\N
54	bla	Siksika	\N	\N	\N
55	bnt	Bantu (Other)	\N	\N	\N
57	bra	Braj	\N	\N	\N
59	btk	Batak (Indonesia)	\N	\N	\N
60	bua	Buriat	\N	\N	\N
61	bug	Buginese	\N	\N	\N
63	my	Burmese	\N	\N	\N
64	byn	Blin; Bilin	\N	\N	\N
65	cad	Caddo	\N	\N	\N
66	cai	Central American Indian (Other)	\N	\N	\N
67	car	Carib	\N	\N	\N
69	cau	Caucasian (Other)	\N	\N	\N
70	ceb	Cebuano	\N	\N	\N
71	cel	Celtic (Other)	\N	\N	\N
72	ch	Chamorro	\N	\N	\N
73	chb	Chibcha	\N	\N	\N
74	ce	Chechen	\N	\N	\N
75	chg	Chagatai	\N	\N	\N
76	zh	Chinese	\N	\N	\N
77	chk	Chukese	\N	\N	\N
78	chm	Mari	\N	\N	\N
79	chn	Chinook jargon	\N	\N	\N
80	cho	Choctaw	\N	\N	\N
81	chp	Chipewyan	\N	\N	\N
82	chr	Cherokee	\N	\N	\N
83	chu	Church Slavic	\N	\N	\N
84	cv	Chuvash	\N	\N	\N
85	chy	Cheyenne	\N	\N	\N
86	cmc	Chamic languages	\N	\N	\N
87	cop	Coptic	\N	\N	\N
88	kw	Cornish	\N	\N	\N
89	co	Corsican	\N	\N	\N
90	cpe	English-based (Other)	\N	\N	\N
91	cpf	French-based (Other)	\N	\N	\N
92	cpp	Portuguese-based (Other)	\N	\N	\N
93	cr	Cree	\N	\N	\N
94	crh	Crimean Turkish; Crimean Tatar	\N	\N	\N
95	crp	Creoles and pidgins (Other)	\N	\N	\N
96	csb	Kashubian	\N	\N	\N
97	cus	Cushitic (Other)	\N	\N	\N
99	dak	Dakota	\N	\N	\N
101	dar	Dargwa	\N	\N	\N
102	del	Delaware	\N	\N	\N
103	den	Slave (Athapascan)	\N	\N	\N
104	dgr	Dogrib	\N	\N	\N
105	din	Dinka	\N	\N	\N
106	dv	Divehi	\N	\N	\N
107	doi	Dogri	\N	\N	\N
108	dra	Dravidian (Other)	\N	\N	\N
109	dsb	Lower Sorbian	\N	\N	\N
110	dua	Duala	\N	\N	\N
111	dum	Dutch, Middle (ca. 1050-1350)	\N	\N	\N
9	af	Afrikaans	Afrikaans	\N	\N
113	dyu	Dyula	\N	\N	\N
114	dz	Dzongkha	\N	\N	\N
115	efi	Efik	\N	\N	\N
116	egy	Egyptian (Ancient)	\N	\N	\N
117	eka	Ekajuk	\N	\N	\N
118	elx	Elamite	\N	\N	\N
18	ar	Arabic	العربية	\N	\N
120	enm	English, Middle (1100-1500)	\N	\N	\N
123	ee	Ewe	\N	\N	\N
124	ewo	Ewondo	\N	\N	\N
125	fan	Fang	\N	\N	\N
127	fat	Fanti	\N	\N	\N
128	fj	Fijian	\N	\N	\N
34	az	Azerbaijani	Azərbaycan türkçəsi	\N	\N
130	fiu	Finno-Ugrian (Other)	\N	\N	\N
131	fon	Fon	\N	\N	\N
41	eu	Basque	Euskara	\N	\N
133	frm	French, Middle (ca.1400-1600)	\N	\N	\N
134	fro	French, Old (842-ca.1400)	\N	\N	\N
135	fy	Frisian	\N	\N	\N
136	ff	Fulah	\N	\N	\N
137	fur	Friulian	\N	\N	\N
138	gaa	Ga	\N	\N	\N
139	gay	Gayo	\N	\N	\N
140	gba	Gbaya	\N	\N	\N
141	gem	Germanic (Other)	\N	\N	\N
142	ka	Georgian	\N	\N	\N
56	bs	Bosnian	Rumunjki	\N	\N
144	gez	Geez	\N	\N	\N
145	gil	Gilbertese	\N	\N	\N
146	gd	Gaelic; Scottish	\N	\N	\N
58	br	Breton	Brezhoneg	\N	\N
149	gv	Manx	\N	\N	\N
150	gmh	German, Middle High (ca.1050-1500)	\N	\N	\N
151	goh	German, Old High (ca.750-1050)	\N	\N	\N
152	gon	Gondi	\N	\N	\N
153	gor	Gorontalo	\N	\N	\N
154	got	Gothic	\N	\N	\N
155	grb	Grebo	\N	\N	\N
156	grc	Greek, Ancient (to 1453)	\N	\N	\N
62	bg	Bulgarian	Български	\N	\N
158	gn	Guarani	\N	\N	\N
159	gu	Gujarati	\N	\N	\N
160	gwi	Gwichin	\N	\N	\N
161	hai	Haida	\N	\N	\N
162	ht	Haitian; Haitian Creole	\N	\N	\N
163	ha	Hausa	\N	\N	\N
164	haw	Hawaiian	\N	\N	\N
68	ca	Catalan	Català	2	n != 1
166	hz	Herero	\N	\N	\N
167	hil	Hiligaynon	\N	\N	\N
168	him	Himachali	\N	\N	\N
169	hi	Hindi	\N	\N	\N
170	hit	Hittite	\N	\N	\N
171	hmn	Hmong	\N	\N	\N
172	ho	Hiri	\N	\N	\N
173	hsb	Upper Sorbian	\N	\N	\N
122	et	Estonian	Eesti	\N	\N
175	hup	Hupa	\N	\N	\N
176	iba	Iban	\N	\N	\N
177	ig	Igbo	\N	\N	\N
179	io	Ido	\N	\N	\N
180	ii	Sichuan Yi	\N	\N	\N
181	ijo	Ijo	\N	\N	\N
182	iu	Inuktitut	\N	\N	\N
183	ie	Interlingue	\N	\N	\N
184	ilo	Iloko	\N	\N	\N
185	ia	Interlingua	\N	\N	\N
186	inc	Indic (Other)	\N	\N	\N
188	ine	Indo-European (Other)	\N	\N	\N
189	inh	Ingush	\N	\N	\N
190	ik	Inupiaq	\N	\N	\N
191	ira	Iranian (Other)	\N	\N	\N
192	iro	Iroquoian languages	\N	\N	\N
148	gl	Gallegan	Galego	\N	\N
194	jv	Javanese	\N	\N	\N
195	jbo	Lojban	\N	\N	\N
178	is	Icelandic	Íslenska	\N	\N
197	jpr	Judeo-Persian	\N	\N	\N
198	jrb	Judeo-Arabic	\N	\N	\N
199	kaa	Kara-Kalpak	\N	\N	\N
200	kab	Kabyle	\N	\N	\N
201	kac	Kachin	\N	\N	\N
202	kl	Greenlandic (Kalaallisut)	\N	\N	\N
203	kam	Kamba	\N	\N	\N
204	kn	Kannada	\N	\N	\N
205	kar	Karen	\N	\N	\N
206	ks	Kashmiri	\N	\N	\N
208	kaw	Kawi	\N	\N	\N
209	kk	Kazakh	\N	\N	\N
210	kbd	Kabardian	\N	\N	\N
211	kha	Khazi	\N	\N	\N
212	khi	Khoisan (Other)	\N	\N	\N
213	km	Khmer	\N	\N	\N
214	kho	Khotanese	\N	\N	\N
215	ki	Kikuyu	\N	\N	\N
216	rw	Kinyarwanda	\N	\N	\N
217	ky	Kirghiz	\N	\N	\N
218	kmb	Kimbundu	\N	\N	\N
220	kv	Komi	\N	\N	\N
221	kg	Kongo	\N	\N	\N
223	kos	Kosraean	\N	\N	\N
224	kpe	Kpelle	\N	\N	\N
225	krc	Karachay-Balkar	\N	\N	\N
226	kro	Kru	\N	\N	\N
227	kru	Kurukh	\N	\N	\N
228	kj	Kuanyama	\N	\N	\N
229	kum	Kumyk	\N	\N	\N
230	ku	Kurdish	\N	\N	\N
231	kut	Kutenai	\N	\N	\N
232	lad	Ladino	\N	\N	\N
233	lah	Lahnda	\N	\N	\N
234	lam	Lamba	\N	\N	\N
235	lo	Lao	\N	\N	\N
236	la	Latin	\N	\N	\N
238	lez	Lezghian	\N	\N	\N
239	li	Limburgian	\N	\N	\N
240	ln	Lingala	\N	\N	\N
242	lol	Mongo	\N	\N	\N
243	loz	Lozi	\N	\N	\N
244	lb	Luxembourgish	\N	\N	\N
245	lua	Luba-Lulua	\N	\N	\N
246	lu	Luba-Katanga	\N	\N	\N
247	lg	Ganda	\N	\N	\N
248	lui	Luiseno	\N	\N	\N
249	lun	Lunda	\N	\N	\N
250	luo	Luo (Kenya and Tanzania)	\N	\N	\N
251	lus	Lushai	\N	\N	\N
253	mad	Madurese	\N	\N	\N
254	mag	Magahi	\N	\N	\N
255	mh	Marshallese	\N	\N	\N
256	mai	Maithili	\N	\N	\N
257	mak	Makasar	\N	\N	\N
258	ml	Malayalam	\N	\N	\N
259	man	Mandingo	\N	\N	\N
261	map	Austronesian (Other)	\N	\N	\N
263	mas	Masai	\N	\N	\N
264	ms	Malay	\N	\N	\N
265	mdf	Moksha	\N	\N	\N
266	mdr	Mandar	\N	\N	\N
267	men	Mende	\N	\N	\N
268	mga	Irish, Middle (900-1200)	\N	\N	\N
269	mic	Micmac	\N	\N	\N
270	min	Minangkabau	\N	\N	\N
271	mis	Miscellaneous languages	\N	\N	\N
272	mkh	Mon-Khmer (Other)	\N	\N	\N
273	mg	Malagasy	\N	\N	\N
275	mnc	Manchu	\N	\N	\N
276	mno	Manobo languages	\N	\N	\N
277	moh	Mohawk	\N	\N	\N
278	mo	Moldavian	\N	\N	\N
280	mos	Mossi	\N	\N	\N
281	mul	Multiple languages	\N	\N	\N
282	mun	Munda languages	\N	\N	\N
283	mus	Creek	\N	\N	\N
284	mwr	Marwari	\N	\N	\N
285	myn	Mayan languages	\N	\N	\N
286	myv	Erzya	\N	\N	\N
287	nah	Nahuatl	\N	\N	\N
288	nai	North American Indian (Other)	\N	\N	\N
289	nap	Neapolitan	\N	\N	\N
290	na	Nauru	\N	\N	\N
291	nv	Navaho	\N	\N	\N
292	nr	Ndebele, South	\N	\N	\N
293	nd	Ndebele, North	\N	\N	\N
294	ng	Ndonga	\N	\N	\N
295	nds	German, Low	\N	\N	\N
296	ne	Nepali	\N	\N	\N
297	new	Newari	\N	\N	\N
298	nia	Nias	\N	\N	\N
299	nic	Niger-Kordofanian (Other)	\N	\N	\N
300	niu	Niuean	\N	\N	\N
301	nn	Norwegian Nynorsk	\N	\N	\N
302	nb	Bokmål, Norwegian	\N	\N	\N
303	nog	Nogai	\N	\N	\N
304	non	Norse, Old	\N	\N	\N
187	id	Indonesian	Masedonian	\N	\N
306	nso	Sotho, Northern	\N	\N	\N
307	nub	Nubian languages	\N	\N	\N
308	nwc	Classical Newari; Old Newari	\N	\N	\N
309	ny	Chewa; Chichewa; Nyanja	\N	\N	\N
310	nym	Nyankole	\N	\N	\N
311	nyo	Nyoro	\N	\N	\N
312	nzi	Nzima	\N	\N	\N
313	oc	Occitan (post 1500)	\N	\N	\N
314	oj	Ojibwa	\N	\N	\N
315	or	Oriya	\N	\N	\N
317	osa	Osage	\N	\N	\N
318	os	Ossetian	\N	\N	\N
319	ota	Turkish, Ottoman (1500-1928)	\N	\N	\N
320	oto	Otomian languages	\N	\N	\N
321	paa	Papuan (Other)	\N	\N	\N
322	pag	Pangasinan	\N	\N	\N
323	pal	Pahlavi	\N	\N	\N
324	pam	Pampanga	\N	\N	\N
325	pa	Panjabi	\N	\N	\N
326	pap	Papiamento	\N	\N	\N
327	pau	Palauan	\N	\N	\N
328	peo	Persian, Old (ca.600-400 B.C.)	\N	\N	\N
330	phi	Philippine (Other)	\N	\N	\N
331	phn	Phoenician	\N	\N	\N
332	pi	Pali	\N	\N	\N
219	kok	Konkani	कॲंकणी	\N	\N
222	ko	Korean	한국어	\N	\N
335	pon	Pohnpeian	\N	\N	\N
336	pra	Prakrit languages	\N	\N	\N
337	pro	Provençal, Old (to 1500)	\N	\N	\N
338	ps	Pushto	\N	\N	\N
339	qu	Quechua	\N	\N	\N
340	raj	Rajasthani	\N	\N	\N
341	rap	Rapanui	\N	\N	\N
342	rar	Rarotongan	\N	\N	\N
343	roa	Romance (Other)	\N	\N	\N
344	rm	Raeto-Romance	\N	\N	\N
345	rom	Romany	\N	\N	\N
347	rn	Rundi	\N	\N	\N
252	mk	Macedonian	Македонски	\N	\N
349	sad	Sandawe	\N	\N	\N
350	sg	Sango	\N	\N	\N
351	sah	Yakut	\N	\N	\N
352	sai	South American Indian (Other)	\N	\N	\N
353	sal	Salishan languages	\N	\N	\N
354	sam	Samaritan Aramaic	\N	\N	\N
355	sa	Sanskrit	\N	\N	\N
356	sas	Sasak	\N	\N	\N
357	sat	Santali	\N	\N	\N
359	sco	Scots	\N	\N	\N
361	sel	Selkup	\N	\N	\N
362	sem	Semitic (Other)	\N	\N	\N
363	sga	Irish, Old (to 900)	\N	\N	\N
364	sgn	Sign languages	\N	\N	\N
365	shn	Shan	\N	\N	\N
366	sid	Sidamo	\N	\N	\N
367	si	Sinhalese	\N	\N	\N
368	sio	Siouan languages	\N	\N	\N
369	sit	Sino-Tibetan (Other)	\N	\N	\N
370	sla	Slavic (Other)	\N	\N	\N
373	sma	Southern Sami	\N	\N	\N
374	se	Northern Sami	\N	\N	\N
375	smi	Sami languages (Other)	\N	\N	\N
376	smj	Lule Sami	\N	\N	\N
377	smn	Inari Sami	\N	\N	\N
378	sm	Samoan	\N	\N	\N
379	sms	Skolt Sami	\N	\N	\N
380	sn	Shona	\N	\N	\N
381	sd	Sindhi	\N	\N	\N
382	snk	Soninke	\N	\N	\N
383	sog	Sogdian	\N	\N	\N
384	so	Somali	\N	\N	\N
385	son	Songhai	\N	\N	\N
386	st	Sotho, Southern	\N	\N	\N
260	mi	Maori	Reo Mäori	\N	\N
388	sc	Sardinian	\N	\N	\N
389	srr	Serer	\N	\N	\N
390	ssa	Nilo-Saharan (Other)	\N	\N	\N
391	ss	Swati	\N	\N	\N
392	suk	Sukuma	\N	\N	\N
393	su	Sundanese	\N	\N	\N
394	sus	Susu	\N	\N	\N
395	sux	Sumerian	\N	\N	\N
262	mr	Marathi	ॕर॥ठी	\N	\N
398	syr	Syriac	\N	\N	\N
399	ty	Tahitian	\N	\N	\N
400	tai	Tai (Other)	\N	\N	\N
402	ts	Tsonga	\N	\N	\N
403	tt	Tatar	\N	\N	\N
405	tem	Timne	\N	\N	\N
406	ter	Tereno	\N	\N	\N
407	tet	Tetum	\N	\N	\N
408	tg	Tajik	\N	\N	\N
409	tl	Tagalog	\N	\N	\N
411	bo	Tibetan	\N	\N	\N
412	tig	Tigre	\N	\N	\N
413	ti	Tigrinya	\N	\N	\N
414	tiv	Tiv	\N	\N	\N
415	tlh	Klingon; tlhIngan-Hol	\N	\N	\N
416	tkl	Tokelau	\N	\N	\N
417	tli	Tlinglit	\N	\N	\N
418	tmh	Tamashek	\N	\N	\N
419	tog	Tonga (Nyasa)	\N	\N	\N
420	to	Tonga (Tonga Islands)	\N	\N	\N
421	tpi	Tok Pisin	\N	\N	\N
422	tsi	Tsimshian	\N	\N	\N
423	tn	Tswana	\N	\N	\N
424	tk	Turkmen	\N	\N	\N
425	tum	Tumbuka	\N	\N	\N
426	tup	Tupi languages	\N	\N	\N
428	tut	Altaic (Other)	\N	\N	\N
429	tvl	Tuvalu	\N	\N	\N
430	tw	Twi	\N	\N	\N
431	tyv	Tuvinian	\N	\N	\N
432	udm	Udmurt	\N	\N	\N
433	uga	Ugaritic	\N	\N	\N
434	ug	Uighur	\N	\N	\N
274	mt	Maltese	Malti	\N	\N
436	umb	Umbundu	\N	\N	\N
437	und	Undetermined	\N	\N	\N
438	urd	Urdu	\N	\N	\N
439	uz	Uzbek	\N	\N	\N
440	vai	Vai	\N	\N	\N
443	vo	Volapuk	\N	\N	\N
444	vot	Votic	\N	\N	\N
445	wak	Wakashan languages	\N	\N	\N
446	wal	Walamo	\N	\N	\N
447	war	Waray	\N	\N	\N
448	was	Washo	\N	\N	\N
450	wen	Sorbian languages	\N	\N	\N
452	wo	Wolof	\N	\N	\N
453	xal	Kalmyk	\N	\N	\N
455	yao	Yao	\N	\N	\N
456	yap	Yapese	\N	\N	\N
457	yi	Yiddish	\N	\N	\N
458	yo	Yoruba	\N	\N	\N
459	ypk	Yupik languages	\N	\N	\N
460	zap	Zapotec	\N	\N	\N
461	zen	Zenaga	\N	\N	\N
462	za	Chuang; Zhuang	\N	\N	\N
463	znd	Zande	\N	\N	\N
465	zun	Zuni	\N	\N	\N
466	ro_RO	Romanian from Romania	\N	\N	\N
467	ar_TN	Arabic from Tunisia	\N	\N	\N
468	pa_IN	Panjabi from India	\N	\N	\N
469	ar_MA	Arabic from Morocco	\N	\N	\N
470	ar_LY	Arabic from Libyan Arab Jamahiriya	\N	\N	\N
471	es_SV	Spanish (Castilian) from El Salvador	\N	\N	\N
472	ga_IE	Irish from Ireland	\N	\N	\N
473	ta_IN	Tamil from India	\N	\N	\N
474	en_HK	English from Hong Kong	\N	\N	\N
475	cs_CZ	Czech from Czech Republic	\N	\N	\N
476	ar_LB	Arabic from Lebanon	\N	\N	\N
477	it_IT	Italian from Italy	\N	\N	\N
478	es_CO	Spanish (Castilian) from Colombia	\N	\N	\N
479	ti_ET	Tigrinya from Ethiopia	\N	\N	\N
480	ar_DZ	Arabic from Algeria	\N	\N	\N
481	de_BE	German from Belgium	\N	\N	\N
482	mk_MK	Macedonian from Macedonia, the Former Yugoslav Republic of	\N	\N	\N
483	gv_GB	Manx from United Kingdom	\N	\N	\N
484	th_TH	Thai from Thailand	\N	\N	\N
485	uz_UZ	Uzbek from Uzbekistan	\N	\N	\N
486	bn_IN	Bengali from India	\N	\N	\N
487	tl_PH	Tagalog from Philippines	\N	\N	\N
488	en_PH	English from Philippines	\N	\N	\N
489	mi_NZ	Maori from New Zealand	\N	\N	\N
490	pl_PL	Polish from Poland	\N	\N	\N
491	ar_YE	Arabic from Yemen	\N	\N	\N
492	az_AZ	Azerbaijani from Azerbaijan	\N	\N	\N
493	es_NI	Spanish (Castilian) from Nicaragua	\N	\N	\N
494	af_ZA	Afrikaans from South Africa	\N	\N	\N
495	ar_QA	Arabic from Qatar	\N	\N	\N
496	kl_GL	Greenlandic (Kalaallisut) from Greenland	\N	\N	\N
497	en_ZA	English from South Africa	\N	\N	\N
498	ja_JP	Japanese from Japan	\N	\N	\N
499	zh_HK	Chinese from Hong Kong	\N	\N	\N
500	en_ZW	English from Zimbabwe	\N	\N	\N
501	so_ET	Somali from Ethiopia	\N	\N	\N
502	lv_LV	Latvian from Latvia	\N	\N	\N
503	tt_RU	Tatar from Russian Federation	\N	\N	\N
504	aa_ET	Afar from Ethiopia	\N	\N	\N
505	ar_IN	Arabic from India	\N	\N	\N
506	aa_ER	Afar from Eritrea	\N	\N	\N
507	se_NO	Northern Sami from Norway	\N	\N	\N
508	en_US	English from United States	\N	\N	\N
509	ar_AE	Arabic from United Arab Emirates	\N	\N	\N
510	mt_MT	Maltese from Malta	\N	\N	\N
511	om_KE	Oromo from Kenya	\N	\N	\N
512	ar_IQ	Arabic from Iraq	\N	\N	\N
513	fr_BE	French from Belgium	\N	\N	\N
514	pt_BR	Portuguese from Brazil	\N	\N	\N
515	es_PR	Spanish (Castilian) from Puerto Rico	\N	\N	\N
516	gu_IN	Gujarati from India	\N	\N	\N
517	sid_ET	Sidamo from Ethiopia	\N	\N	\N
518	wa_BE	Walloon from Belgium	\N	\N	\N
519	oc_FR	Occitan (post 1500) from France	\N	\N	\N
520	en_BW	English from Botswana	\N	\N	\N
521	om_ET	Oromo from Ethiopia	\N	\N	\N
522	hi_IN	Hindi from India	\N	\N	\N
523	es_VE	Spanish (Castilian) from Venezuela	\N	\N	\N
524	an_ES	Aragonese from Spain	\N	\N	\N
525	it_CH	Italian from Switzerland	\N	\N	\N
526	da_DK	Danish from Denmark	\N	\N	\N
527	es_AR	Spanish (Castilian) from Argentina	\N	\N	\N
528	ne_NP	Nepali from Nepal	\N	\N	\N
529	sq_AL	Albanian from Albania	\N	\N	\N
530	hu_HU	Hungarian from Hungary	\N	\N	\N
531	sk_SK	Slovak from Slovakia	\N	\N	\N
532	mn_MN	Mongolian from Mongolia	\N	\N	\N
533	ar_KW	Arabic from Kuwait	\N	\N	\N
534	ar_SA	Arabic from Saudi Arabia	\N	\N	\N
535	ar_SD	Arabic from Sudan	\N	\N	\N
536	pt_PT	Portuguese from Portugal	\N	\N	\N
537	nn_NO	Norwegian Nynorsk from Norway	\N	\N	\N
538	ar_SY	Arabic from Syrian Arab Republic	\N	\N	\N
539	byn_ER	Blin; Bilin from Eritrea	\N	\N	\N
540	en_GB	English from United Kingdom	\N	\N	\N
541	et_EE	Estonian from Estonia	\N	\N	\N
542	lt_LT	Lithuanian from Lithuania	\N	\N	\N
543	zu_ZA	Zulu from South Africa	\N	\N	\N
544	zh_SG	Chinese from Singapore	\N	\N	\N
545	es_DO	Spanish (Castilian) from Dominican Republic	\N	\N	\N
546	lg_UG	Ganda from Uganda	\N	\N	\N
547	id_ID	Indonesian from Indonesia	\N	\N	\N
548	hr_HR	Croatian from Croatia	\N	\N	\N
549	es_CL	Spanish (Castilian) from Chile	\N	\N	\N
550	sl_SI	Slovenian from Slovenia	\N	\N	\N
551	is_IS	Icelandic from Iceland	\N	\N	\N
552	gez_ER	Geez from Eritrea	\N	\N	\N
553	fo_FO	Faroese from Faroe Islands	\N	\N	\N
554	bs_BA	Bosnian from Bosnia and Herzegovina	\N	\N	\N
555	ti_ER	Tigrinya from Eritrea	\N	\N	\N
556	en_DK	English from Denmark	\N	\N	\N
557	no_NO	Norwegian from Norway	\N	\N	\N
558	eu_ES	Basque from Spain	\N	\N	\N
559	kw_GB	Cornish from United Kingdom	\N	\N	\N
560	ms_MY	Malay from Malaysia	\N	\N	\N
561	kn_IN	Kannada from India	\N	\N	\N
562	es_GT	Spanish (Castilian) from Guatemala	\N	\N	\N
563	be_BY	Belarusian from Belarus	\N	\N	\N
564	vi_VN	Vietnamese from Viet Nam	\N	\N	\N
565	fr_CA	French from Canada	\N	\N	\N
566	aa_DJ	Afar from Djibouti	\N	\N	\N
567	fr_CH	French from Switzerland	\N	\N	\N
568	fi_FI	Finnish from Finland	\N	\N	\N
569	so_DJ	Somali from Djibouti	\N	\N	\N
570	en_IN	English from India	\N	\N	\N
571	en_AU	English from Australia	\N	\N	\N
572	en_IE	English from Ireland	\N	\N	\N
573	tr_TR	Turkish from Turkey	\N	\N	\N
574	bn_BD	Bengali from Bangladesh	\N	\N	\N
575	ru_UA	Russian from Ukraine	\N	\N	\N
576	gd_GB	Gaelic; Scottish from United Kingdom	\N	\N	\N
577	nl_BE	Dutch from Belgium	\N	\N	\N
578	de_CH	German from Switzerland	\N	\N	\N
579	es_BO	Spanish (Castilian) from Bolivia	\N	\N	\N
580	te_IN	Telugu from India	\N	\N	\N
581	zh_TW	Chinese from Taiwan, Province of China	\N	\N	\N
582	xh_ZA	Xhosa from South Africa	\N	\N	\N
583	es_CR	Spanish (Castilian) from Costa Rica	\N	\N	\N
584	am_ET	Amharic from Ethiopia	\N	\N	\N
585	gez_ET	Geez from Ethiopia	\N	\N	\N
586	ar_EG	Arabic from Egypt	\N	\N	\N
587	ca_ES	Catalan from Spain	\N	\N	\N
588	fr_FR	French from France	\N	\N	\N
589	zh_CN	Chinese from China	\N	\N	\N
590	es_UY	Spanish (Castilian) from Uruguay	\N	\N	\N
591	tg_TJ	Tajik from Tajikistan	\N	\N	\N
592	nl_NL	Dutch from Netherlands	\N	\N	\N
593	es_US	Spanish (Castilian) from United States	\N	\N	\N
594	yi_US	Yiddish from United States	\N	\N	\N
595	ml_IN	Malayalam from India	\N	\N	\N
596	uk_UA	Ukrainian from Ukraine	\N	\N	\N
597	de_LU	German from Luxembourg	\N	\N	\N
598	st_ZA	Sotho, Southern from South Africa	\N	\N	\N
599	es_MX	Spanish (Castilian) from Mexico	\N	\N	\N
600	ar_JO	Arabic from Jordan	\N	\N	\N
601	fa_IR	Persian from Iran, Islamic Republic of	\N	\N	\N
602	lo_LA	Lao from Lao People's Democratic Republic	\N	\N	\N
603	es_EC	Spanish (Castilian) from Ecuador	\N	\N	\N
604	so_KE	Somali from Kenya	\N	\N	\N
605	en_NZ	English from New Zealand	\N	\N	\N
606	he_IL	Hebrew from Israel	\N	\N	\N
607	sv_SE	Swedish from Sweden	\N	\N	\N
608	ru_RU	Russian from Russian Federation	\N	\N	\N
609	cy_GB	Welsh from United Kingdom	\N	\N	\N
610	br_FR	Breton from France	\N	\N	\N
611	el_GR	Greek, Modern (1453-) from Greece	\N	\N	\N
612	es_ES	Spanish (Castilian) from Spain	\N	\N	\N
613	ar_BH	Arabic from Bahrain	\N	\N	\N
614	bg_BG	Bulgarian from Bulgaria	\N	\N	\N
615	de_DE	German from Germany	\N	\N	\N
616	gl_ES	Gallegan from Spain	\N	\N	\N
617	mr_IN	Marathi from India	\N	\N	\N
618	en_CA	English from Canada	\N	\N	\N
619	es_PY	Spanish (Castilian) from Paraguay	\N	\N	\N
620	so_SO	Somali from Somalia	\N	\N	\N
621	fr_LU	French from Luxembourg	\N	\N	\N
622	ar_OM	Arabic from Oman	\N	\N	\N
623	es_PA	Spanish (Castilian) from Panama	\N	\N	\N
624	sv_FI	Swedish from Finland	\N	\N	\N
625	ka_GE	Georgian from Georgia	\N	\N	\N
626	es_PE	Spanish (Castilian) from Peru	\N	\N	\N
627	nb_NO	Bokmål, Norwegian from Norway	\N	\N	\N
628	tig_ER	Tigre from Eritrea	\N	\N	\N
629	es_HN	Spanish (Castilian) from Honduras	\N	\N	\N
630	ko_KR	Korean from Korea, Republic of	\N	\N	\N
631	de_AT	German from Austria	\N	\N	\N
632	en_SG	English from Singapore	\N	\N	\N
119	en	English	\N	2	n != 1
126	fo	Faroese	\N	2	n != 1
207	kr	Kanuri	\N	1	0
98	cs	Czech	Čeština	3	n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2
100	da	Danish	Dansk	2	n != 1
112	nl	Dutch	Nederlands	2	n != 1
121	eo	Esperanto	Esperanto	2	n != 1
129	fi	Finnish	Suomi	2	n != 1
132	fr	French	français	2	n > 1
143	de	German	Deutsch	2	n != 1
147	ga	Irish	Gaeilge	3	n==1 ? 0 : n==2 ? 1 : 2
157	el	Greek, Modern (1453-)	Σύγχρονα Ελληνικά (1453-)	2	n != 1
165	he	Hebrew	עברית	2	n != 1
174	hu	Hungarian	magyar	1	0
193	it	Italian	Italiano	2	n != 1
196	ja	Japanese	日本語	1	0
237	lv	Latvian	Latviešu	3	n%10==1 && n%100!=11 ? 0 : n != 0 ? 1 : 2
241	lt	Lithuanian	Lietuvių	3	n%10==1 && n%100!=11 ? 0 : n%10>=2 && (n%100<10 || n%100>=20) ? 1 : 2
279	mn	Mongolian	Монгол	\N	\N
305	no	Norwegian	Norsk	2	n != 1
316	om	Oromo	Oromoo	\N	\N
329	fa	Persian	فارسی	\N	\N
333	pl	Polish	Polski	3	n==1 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2
334	pt	Portuguese	Português	2	n != 1
346	ro	Romanian	Română	\N	\N
348	ru	Russian	Русский	3	n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2
358	sr	Serbian	Srpski	\N	\N
360	hr	Croatian	Hrvatski	3	n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2
371	sk	Slovak	Slovenský	3	n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2
372	sl	Slovenian	Slovenščina	\N	\N
387	es	Spanish (Castilian)	Español, Castellano	2	n != 1
396	sw	Swahili	Kiswahili	\N	\N
397	sv	Swedish	Svenska	2	n != 1
401	ta	Tamil	¾Á¢ú	\N	\N
404	te	Telugu	㌤㍆㌲㍁㌗㍁	\N	\N
410	th	Thai	ไทย	\N	\N
427	tr	Turkish	Türkçe	\N	\N
435	uk	Ukrainian	Українська	3	n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2
441	ve	Venda	Venda	\N	\N
442	vi	Vietnamese	Nam=Nho 	\N	\N
449	cy	Welsh	Cymraeg	4	n==1 ? 0 : n==2 ? 1 : (n != 8 || n != 11) ? 2 : 3
451	wa	Walloon	Walon	\N	\N
454	xh	Xhosa	XChat	\N	\N
464	zu	Zulu	Isi-Zulu	\N	\N
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


