#!/usr/bin/env python
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Origins dictionary containing all mirrors used for sync-source.py."""

__all__ = ['origins']

origins = {

"debian": {
    "name": "Debian",
    "url": "http://ftp.debian.org/debian/",
    "default suite": "unstable",
    "default component": "main",
    "dsc": "must be signed and valid"
    },

"security": {
    "name": "Security",
    "url": "http://security.debian.org/debian-security/",
    "default suite": "etch/updates",
    "default component": "main",
    "dsc": "must be signed and valid"
    },

"incoming": {
    "name": "Debian",
    "url": "http://incoming.debian.org/",
    "default suite": "incoming",
    "default component": "main",
    "dsc": "must be signed and valid"
    },

"blackdown": {
    "name": "Blackdown",
    "url": "http://ftp.gwdg.de/pub/languages/java/linux/debian/",
    "default suite": "unstable",
    "default component": "non-free",
    "dsc": "must be signed and valid"
    },

"marillat": {
    "name": "Marillat",
    "url": "ftp://ftp.nerim.net/debian-marillat/",
    "default suite": "unstable",
    "default component": "main",
    "dsc": "can be unsigned"
    },

"mythtv": {
    "name": "MythTV",
    "url": "http://dijkstra.csh.rit.edu/~mdz/debian/",
    "default suite": "unstable",
    "default component": "mythtv",
    "dsc": "can be unsigned"
    },

"xfce": {
    "name": "XFCE",
    "url": "http://www.os-works.com/debian/",
    "default suite": "testing",
    "default component": "main",
    "dsc": "must be signed and valid"
    },

####################################

"apt.logreport.org-pub-debian": {
    "name": "apt.logreport.org-pub-debian",
    "url": "http://apt.logreport.org/pub/debian/",
    "default suite": "local",
    "default component": "contrib",
    "dsc": "can be unsigned"
    },

"apt.pgpackages.org-debian": {
    "name": "apt.pgpackages.org-debian",
    "url": "http://apt.pgpackages.org/debian/",
    "default suite": "sid",
    "default component": "non-free",
    "dsc": "can be unsigned"
    },

"arda.lt-p.net-debian": {
    "name": "arda.LT-P.net-debian",
    "url": "http://arda.LT-P.net/debian/",
    "default suite": "",
    "default component": "",
    "dsc": "can be unsigned"
    },

"colo.khms.westfalen.de-pakete": {
    "name": "colo.khms.westfalen.de-Pakete",
    "url": "http://colo.khms.westfalen.de/Pakete/",
    "default suite": "unstable",
    "default component": "",
    "dsc": "can be unsigned"
    },

"debian.speedblue.org": {
    "name": "debian.speedblue.org",
    "url": "http://debian.speedblue.org/",
    "default suite": "",
    "default component": "",
    "dsc": "can be unsigned"
    },

"dl.gna.org-kazehakase": {
    "name": "dl.gna.org-kazehakase",
    "url": "http://dl.gna.org/kazehakase/",
    "default suite": "debian",
    "default component": "",
    "dsc": "can be unsigned"
    },

"elonen.iki.fi-code-unofficial-debs": {
    "name": "elonen.iki.fi-code-unofficial-debs",
    "url": "http://elonen.iki.fi/code/unofficial-debs/",
    "default suite": "",
    "default component": "",
    "dsc": "can be unsigned"
    },

"erlug.linux.it-%7eda-deb": {
    "name": "erlug.linux.it-%7Eda-deb",
    "url": "http://erlug.linux.it/~da/deb/",
    "default suite": "",
    "default component": "",
    "dsc": "can be unsigned"
    },

"ftp.arege.jp-debian-arege": {
    "name": "ftp.arege.jp-debian-arege",
    "url": "http://ftp.arege.jp/debian-arege/",
    "default suite": "sid",
    "default component": "ALL",
    "dsc": "can be unsigned"
    },

"instantafs.cbs.mpg.de-instantafs-sid": {
    "name": "instantafs.cbs.mpg.de-instantafs-sid",
    "url": "ftp://instantafs.cbs.mpg.de/instantafs/sid/",
    "default suite": "",
    "default component": "",
    "dsc": "can be unsigned"
    },

"jeroen.coekaerts.be-debian": {
    "name": "jeroen.coekaerts.be-debian",
    "url": "http://jeroen.coekaerts.be/debian/",
    "default suite": "unstable",
    "default component": "non-free",
    "dsc": "can be unsigned"
    },

"laylward.com-debian": {
    "name": "laylward.com-debian",
    "url": "http://laylward.com/debian/",
    "default suite": "unstable",
    "default component": "",
    "dsc": "can be unsigned"
    },

"mherrn.de-debian": {
    "name": "mherrn.de-debian",
    "url": "http://mherrn.de/debian/",
    "default suite": "sid",
    "default component": "exim",
    "dsc": "can be unsigned"
    },

"mulk.dyndns.org-apt": {
    "name": "mulk.dyndns.org-apt",
    "url": "http://mulk.dyndns.org/apt/",
    "default suite": "unstable",
    "default component": "main",
    "dsc": "can be unsigned"
    },

"opensource.polytechnique.org-debian": {
    "name": "opensource.polytechnique.org-debian",
    "url": "http://opensource.polytechnique.org/debian/",
    "default suite": "",
    "default component": "",
    "dsc": "can be unsigned"
    },

"people.debian.org-%7eamaya-debian": {
    "name": "people.debian.org-%7Eamaya-debian",
    "url": "http://people.debian.org/~amaya/debian/",
    "default suite": "",
    "default component": "",
    "dsc": "can be unsigned"
    },

"people.debian.org-%7ecostela-debian": {
    "name": "people.debian.org-%7Ecostela-debian",
    "url": "http://people.debian.org/~costela/debian/",
    "default suite": "",
    "default component": "",
    "dsc": "can be unsigned"
    },

"people.debian.org-%7ercardenes": {
    "name": "people.debian.org-%7Ercardenes",
    "url": "http://people.debian.org/~rcardenes/",
    "default suite": "sid",
    "default component": "main",
    "dsc": "can be unsigned"
    },

"piem.homeip.net-%7epiem-debian": {
    "name": "piem.homeip.net-%7Epiem-debian",
    "url": "http://piem.homeip.net/~piem/debian/",
    "default suite": "source",
    "default component": "",
    "dsc": "can be unsigned"
    },

"progn.org-debian": {
    "name": "progn.org-debian",
    "url": "ftp://progn.org/debian/",
    "default suite": "unstable",
    "default component": "main",
    "dsc": "can be unsigned"
    },

"ressukka.net-%7eressu-deb": {
    "name": "ressukka.net-%7Eressu-deb",
    "url": "http://ressukka.net/~ressu/deb/",
    "default suite": "unstable",
    "default component": "",
    "dsc": "can be unsigned"
    },

"sadleder.de-debian": {
    "name": "sadleder.de-debian",
    "url": "http://sadleder.de/debian/",
    "default suite": "",
    "default component": "",
    "dsc": "can be unsigned"
    },

"security.dsi.unimi.it-%7elorenzo-debian": {
    "name": "security.dsi.unimi.it-%7Elorenzo-debian",
    "url": "http://security.dsi.unimi.it/~lorenzo/debian/",
    "default suite": "",
    "default component": "",
    "dsc": "can be unsigned"
    },

"src.braincells.com-debian": {
    "name": "src.braincells.com-debian",
    "url": "http://src.braincells.com/debian/",
    "default suite": "sid",
    "default component": "",
    "dsc": "can be unsigned"
    },

"themind.altervista.org-debian": {
    "name": "themind.altervista.org-debian",
    "url": "http://themind.altervista.org/debian/",
    "default suite": "unstable",
    "default component": "main",
    "dsc": "can be unsigned"
    },

"www.cps-project.org-debian-unstable": {
    "name": "www.cps-project.org-debian-unstable",
    "url": "http://www.cps-project.org/debian/unstable/",
    "default suite": "",
    "default component": "",
    "dsc": "can be unsigned"
    },

"www.gwhere.org-download-debian": {
    "name": "www.gwhere.org-download-debian",
    "url": "http://www.gwhere.org/download/debian/",
    "default suite": "unstable",
    "default component": "main",
    "dsc": "can be unsigned"
    },

"www.knizefamily.net-russ-software-debian": {
    "name": "www.knizefamily.net-russ-software-debian",
    "url": "http://www.knizefamily.net/russ/software/debian/",
    "default suite": "",
    "default component": "",
    "dsc": "can be unsigned"
    },

"www.litux.org-debian": {
    "name": "www.litux.org-debian",
    "url": "http://www.litux.org/debian/",
    "default suite": "unstable",
    "default component": "",
    "dsc": "can be unsigned"
    },

"www.steve.org.uk-apt": {
    "name": "www.steve.org.uk-apt",
    "url": "http://www.steve.org.uk/apt/",
    "default suite": "",
    "default component": "",
    "dsc": "can be unsigned"
    },

"www.stuff.demon.co.uk-apt": {
    "name": "www.stuff.demon.co.uk-apt",
    "url": "http://www.stuff.demon.co.uk/apt/",
    "default suite": "source",
    "default component": "",
    "dsc": "can be unsigned"
    },

"www.thomas-alfeld.de-frank-download-debian": {
    "name": "www.thomas-alfeld.de-frank-download-debian",
    "url": "http://www.thomas-alfeld.de/frank/download/debian/",
    "default suite": "",
    "default component": "",
    "dsc": "can be unsigned"
    },

"www.zero-based.org-debian": {
    "name": "www.zero-based.org-debian",
    "url": "http://www.zero-based.org/debian/",
    "default suite": "packagessource",
    "default component": "",
    "dsc": "can be unsigned"
    },

"kitenet.net-%7ejoey-debian": {
    "name": "kitenet.net-%7Ejoey-debian",
    "url": "http://kitenet.net/~joey/debian/",
    "default suite": "unstable",
    "default component": "",
    "dsc": "can be unsigned"
    },

"www.roughtrade.net-debian": {
    "name": "www.roughtrade.net-debian",
    "url": "http://www.roughtrade.net/debian/",
    "default suite": "sid",
    "default component": "main",
    "dsc": "can be unsigned"
    },

"telepathy.freedesktop.org-debian": {
    "name": "telepathy.freedesktop.org-debian",
    "url": "http://telepathy.freedesktop.org/debian/",
    "default suite": "sid",
    "default component": "",
    "dsc": "can be unsigned"
    },

####################################

"ftp.mowgli.ch-pub-debian": {
    "name": "ftp.mowgli.ch-pub-debian",
    "url": "ftp://ftp.mowgli.ch/pub/debian/",
    "default suite": "sid",
    "default component": "unofficial",
    "dsc": "can be unsigned"
    },

"http.debian.or.jp-debian-jp": {
    "name": "http.debian.or.jp-debian-jp",
    "url": "http://http.debian.or.jp/debian-jp/",
    "default suite": "unstable-jp",
    "default component": "non-free",
    "dsc": "can be unsigned"
    },

"mywebpages.comcast.net-ddamian-deb": {
    "name": "mywebpages.comcast.net-ddamian-deb",
    "url": "http://mywebpages.comcast.net/ddamian/deb/",
    "default suite": "",
    "default component": "",
    "dsc": "can be unsigned"
    },

"people.debian.org-%7etora-deb": {
    "name": "people.debian.org-%7Etora-deb",
    "url": "http://people.debian.org/~tora/deb/",
    "default suite": "",
    "default component": "",
    "dsc": "can be unsigned"
    },

"silcnet.org-download-client-deb": {
    "name": "silcnet.org-download-client-deb",
    "url": "http://silcnet.org/download/client/deb/",
    "default suite": "",
    "default component": "",
    "dsc": "can be unsigned"
    },

"www.h.shuttle.de-mitch-stuff": {
    "name": "www.h.shuttle.de-mitch-stuff",
    "url": "http://www.h.shuttle.de/mitch/stuff/",
    "default suite": "",
    "default component": "",
    "dsc": "can be unsigned"
    },

"www.assist.media.nagoya-u.ac.jp-%7ekatsu-debian": {
    "name": "www.assist.media.nagoya-u.ac.jp-%7Ekatsu-debian",
    "url": "http://www.assist.media.nagoya-u.ac.jp/~katsu/debian/",
    "default suite": "unstable",
    "default component": "ALL",
    "dsc": "can be unsigned"
    },

"www.stud.tu-ilmenau.de-%7ethsc-in-debian": {
    "name": "www.stud.tu-ilmenau.de-%7Ethsc-in-debian",
    "url": "http://www.stud.tu-ilmenau.de/~thsc-in/debian/",
    "default suite": "unstable",
    "default component": "main",
    "dsc": "can be unsigned"
    },

"debian.hinterhof.net": {
    "name": "debian.hinterhof.net",
    "url": "http://debian.hinterhof.net/",
    "default suite": "unstable",
    "default component": "",
    "dsc": "can be unsigned"
    },

"home.planet.nl-%7eautar022": {
    "name": "home.planet.nl-%7Eautar022",
    "url": "http://home.planet.nl/~autar022/",
    "default suite": "",
    "default component": "",
    "dsc": "can be unsigned"
    },

"dept-info.labri.fr-%7edanjean-debian": {
    "name": "dept-info.labri.fr-%7Edanjean-debian",
    "url": "http://dept-info.labri.fr/~danjean/debian/",
    "default suite": "unstable",
    "default component": "main",
    "dsc": "can be unsigned"
    },

"noxa.de-%7esbeyer-debian": {
    "name": "noxa.de-%7Esbeyer-debian",
    "url": "http://noxa.de/~sbeyer/debian/",
    "default suite": "unstable",
    "default component": "main",
    "dsc": "can be unsigned"
    },

"debian.wgdd.de-debian": {
    "name": "debian.wgdd.de-debian",
    "url": "http://debian.wgdd.de/debian/",
    "default suite": "sid",
    "default component": "non-free",
    "dsc": "can be unsigned"
    },

"luca.pca.it-debian": {
    "name": "luca.pca.it-debian",
    "url": "http://luca.pca.it/debian/",
    "default suite": "",
    "default component": "",
    "dsc": "can be unsigned"
    },

"www.pcxperience.org-apt-debian": {
    "name": "www.pcxperience.org-apt-debian",
    "url": "http://www.pcxperience.org/apt/debian/",
    "default suite": "unstable",
    "default component": "",
    "dsc": "can be unsigned"
    },

"ftp.berlios.de-pub-gift-fasttrack": {
    "name": "ftp.berlios.de-pub-gift-fasttrack",
    "url": "ftp://ftp.berlios.de/pub/gift-fasttrack/",
    "default suite": "unstable",
    "default component": "main",
    "dsc": "can be unsigned"
    },

"www.webalice.it-hayarms-debian": {
    "name": "www.webalice.it-hayarms-debian",
    "url": "http://www.webalice.it/hayarms/debian/",
    "default suite": "unstable",
    "default component": "non-free",
    "dsc": "can be unsigned"
    },

"users.adelphia.net-%7edavid.everly": {
    "name": "users.adelphia.net-%7Edavid.everly",
    "url": "http://users.adelphia.net/~david.everly/",
    "default suite": "emilda/sarge",
    "default component": "",
    "dsc": "can be unsigned"
    },

"debian.thk-systems.de-debian": {
    "name": "debian.thk-systems.de-debian",
    "url": "http://debian.thk-systems.de/debian/",
    "default suite": "unstable",
    "default component": "",
    "dsc": "can be unsigned"
    },

"www.adebenham.com-debian": {
    "name": "www.adebenham.com-debian",
    "url": "http://www.adebenham.com/debian/",
    "default suite": "",
    "default component": "",
    "dsc": "can be unsigned"
    },

"eric.lavar.de-comp-linux-debian": {
    "name": "eric.lavar.de-comp-linux-debian",
    "url": "http://eric.lavar.de/comp/linux/debian/",
    "default suite": "experimental",
    "default component": "",
    "dsc": "can be unsigned"
    },

"einsteinmg.dyndns.org-debian": {
    "name": "einsteinmg.dyndns.org-debian",
    "url": "http://einsteinmg.dyndns.org/debian/",
    "default suite": "unstable",
    "default component": "",
    "dsc": "can be unsigned"
    },

"www.toastfreeware.priv.at-debian": {
    "name": "www.toastfreeware.priv.at-debian",
    "url": "http://www.toastfreeware.priv.at/debian/",
    "default suite": "unstable",
    "default component": "",
    "dsc": "can be unsigned"
    },

"www.riteh.hr-%7evedranf-debian-unstable": {
    "name": "www.riteh.hr-%7Evedranf-debian-unstable",
    "url": "http://www.riteh.hr/~vedranf/debian_unstable/",
    "default suite": "",
    "default component": "",
    "dsc": "can be unsigned"
    },

"ftp.unixdev.net-pub-debian-udev": {
    "name": "ftp.unixdev.net-pub-debian-udev",
    "url": "http://ftp.unixdev.net/pub/debian-udev/",
    "default suite": "unixdev",
    "default component": "non-free",
    "dsc": "can be unsigned"
    },

"packages.kirya.net": {
    "name": "packages.kirya.net",
    "url": "http://packages.kirya.net/",
    "default suite": "unstable",
    "default component": "non-free",
    "dsc": "can be unsigned"
    },

"repos.knio.it": {
    "name": "repos.knio.it",
    "url": "http://repos.knio.it/",
    "default suite": "unstable",
    "default component": "non-free",
    "dsc": "can be unsigned"
    },

"www.wakhok.ac.jp-%7efujimura-debian": {
    "name": "www.wakhok.ac.jp-%7Efujimura-debian",
    "url": "http://www.wakhok.ac.jp/~fujimura/debian/",
    "default suite": "",
    "default component": "",
    "dsc": "can be unsigned"
    },

"www.eto.to-deb": {
    "name": "www.eto.to-deb",
    "url": "http://www.eto.to/deb/",
    "default suite": "",
    "default component": "",
    "dsc": "can be unsigned"
    },

"y-imai.good-day.net-debian": {
    "name": "y-imai.good-day.net-debian",
    "url": "http://y-imai.good-day.net/debian/",
    "default suite": "",
    "default component": "",
    "dsc": "can be unsigned"
    },

"people.realnode.com-%7emnordstr": {
    "name": "people.realnode.com-%7Emnordstr",
    "url": "http://people.realnode.com/~mnordstr/",
    "default suite": "package",
    "default component": "",
    "dsc": "can be unsigned"
    },

"rapid.dotsrc.org": {
    "name": "rapid.dotsrc.org",
    "url": "http://rapid.dotsrc.org/",
    "default suite": "unstable",
    "default component": "",
    "dsc": "can be unsigned"
    },

"debian-eclipse.wfrag.org-debian": {
    "name": "debian-eclipse.wfrag.org-debian",
    "url": "http://debian-eclipse.wfrag.org/debian/",
    "default suite": "sid",
    "default component": "non-free",
    "dsc": "can be unsigned"
    },

"www.stanchina.net-%7eflavio-debian": {
    "name": "www.stanchina.net-%7Eflavio-debian",
    "url": "http://www.stanchina.net/~flavio/debian/",
    "default suite": "",
    "default component": "",
    "dsc": "can be unsigned"
    },

"kibi.dyndns.org-packages": {
    "name": "kibi.dyndns.org-packages",
    "url": "http://kibi.dyndns.org/packages/",
    "default suite": "",
    "default component": "",
    "dsc": "can be unsigned"
    },

"download.gna.org-wormux-debs": {
    "name": "download.gna.org-wormux-debs",
    "url": "http://download.gna.org/wormux/debs/",
    "default suite": "dapper",
    "default component": "",
    "dsc": "can be unsigned"
    },

"apt.alittletooquiet.net-staging": {
    "name": "apt.alittletooquiet.net-staging",
    "url": "http://apt.alittletooquiet.net/staging/",
    "default suite": "dapper",
    "default component": "main",
    "dsc": "can be unsigned"
    },

"www.debian-multimedia.org": {
    "name": "www.debian-multimedia.org",
    "url": "http://www.debian-multimedia.org/",
    "default suite": "unstable",
    "default component": "main",
    "dsc": "can be unsigned",
    },

"repository.maemo.org": {
    "name": "Maemo",
    "url": "http://repository.maemo.org/",
    "default suite": "bora",
    "default component": "free",
    "dsc": "can be unsigned",
    },

"mirror.err.no-uqm": {
    "name": "mirror.err.no-uqm",
    "url": "http://mirror.err.no/uqm/",
    "default suite": "unstable",
    "default component": "",
    "dsc": "can be unsigned"
    },

}
