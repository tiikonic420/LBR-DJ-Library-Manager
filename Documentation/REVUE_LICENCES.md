# Revue technique des licences â€” R10

Ã‰tat au 2 novembre 2026 : revue des 16 distributions Python inventoriÃ©es et des composants natifs identifiÃ©s dans le MSI SHA256 `86dceabb773f6d8d601b3dcbc56d1dfacf40dead517deb8b4ca87e5fe6a00228`. Aucun moteur, TaskHub, SQLite ou test modifiÃ©. Aucun conflit de licence identifiÃ© dans les Ã©lÃ©ments examinÃ©s avec l'option GPL-3.0-or-later du code original ; cette conclusion reste limitÃ©e Ã  ces fichiers et versions.

| Distribution | Version | Licence / pÃ©rimÃ¨tre |
| --- | --- | --- |
| bidict | 0.24.1 | MPL-2.0 |
| construct | 2.10.70 | MIT |
| greenlet | 3.2.4 | MIT AND Python-2.0 |
| mutagen | 1.48.1 | GPL-2.0-or-later |
| numpy | 2.2.6 | BSD-3-Clause + notices incorporÃ©es, exception GCC |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause |
| pillow | 12.3.0 | MIT-CMU |
| pip | 26.2.1 | MIT + licences des composants vendus |
| psutil | 7.0.0 | BSD-3-Clause |
| pyrekordbox | 0.4.4 | MIT |
| python-dateutil | 2.9.0.post0 | BSD-3-Clause OU Apache-2.0 |
| rekordbox-playlist-sync | 0.2.0 | MIT |
| six | 1.17.0 | MIT |
| SQLAlchemy | 2.0.44 | MIT |
| sqlcipher3-wheels | 0.5.7 | Zlib (wrapper) + BSD-3-Clause SQLCipher + Apache-2.0 OpenSSL |
| typing_extensions | 4.16.0 | PSF-2.0 |

## Notices, sources et composants natifs

- Mutagen : texte GPL et archive source 1.48.1 fournis ; GPL-2.0-or-later autorise l'option version 3. rbsync : archive source et licence MIT fournies. bidict : licence MPL-2.0 et code Python en clair livrÃ©s ; conserver et rendre disponibles ces sources lors de la redistribution.
- CPython 3.13.16 : licence PSF et licences incorporÃ©es fournies. Le SBOM officiel du programme d'installation amont a servi d'inventaire complÃ©mentaire, sans Ãªtre prÃ©sentÃ© comme le SBOM complet de LBR. Les DLL OpenSSL et SQLCipher du MSI sont identiques par SHA256 Ã  celles du runtime interrogÃ© en mÃ©moire.
- SQLCipher 4.12.0 Community / SQLite 3.51.1 dans sqlcipher3-wheels 0.5.7 : wrapper Zlib, SQLCipher BSD-3-Clause, base SQLite domaine public. Version obtenue par base en mÃ©moire, confirmÃ©e par l'amalgamation de l'archive source PyPI vÃ©rifiÃ©e. Notice BSD SQLCipher ajoutÃ©e.
- OpenSSL 3.5.9 pour Python et 3.6.0 liÃ© au module SQLCipher : licences Apache-2.0 officielles ajoutÃ©es pour les deux versions. Versions confirmÃ©es par le runtime et les chaÃ®nes des binaires dont les empreintes sont contrÃ´lÃ©es. Les chemins NOTICE et NOTICE.txt des deux tags renvoient 404 ; aucune notice inexistante n'est inventÃ©e.
- Expat 2.8.5, zlib 1.3.1 et liblzma/XZ 5.2.5 : versions inventoriÃ©es dans le SBOM CPython officiel ; copies des notices officielles ajoutÃ©es. liblzma est dÃ©crit comme domaine public dans COPYING ; les licences des outils XZ ne sont pas appliquÃ©es automatiquement Ã  la seule bibliothÃ¨que.
- Tcl/Tk 8.6 : notices dÃ©jÃ  prÃ©sentes dans Python.txt et le runtime. libffi, bzip2 et composants Python incorporÃ©s : notices Python conservÃ©es.
- NumPy 2.2.6 : conserver la notice intÃ©grale incluant OpenBLAS, LAPACK et l'exception d'exÃ©cution GCC. Ne pas prÃ©tendre que tout NumPy est sous GPL ni retirer l'exception.
- Pillow 12.3.0 : conserver la notice intÃ©grale, qui comporte les notices de ses bibliothÃ¨ques incorporÃ©es, notamment FreeType, JPEG, AVIF, WebP et Brotli ; attribution FreeType ajoutÃ©e aux documents de redistribution.
- pip 26.2.1 : ses notices et celles des dÃ©pendances vendues sont prÃ©sentes dans le runtime. Leur licence n'est pas rÃ©duite Ã  celle du seul outil pip.
- vcruntime140, vcruntime140_1 et msvcp140 de NumPy : bibliothÃ¨ques d'exÃ©cution systÃ¨me Microsoft, distinctes du code GPL LBR. Les conditions de redistribution Windows s'appliquent ; les avis ne doivent pas Ãªtre supprimÃ©s. Aucun droit de signature de ces DLL n'est revendiquÃ©.
- FFmpeg 9.0.2 : outil des tests CI, absent du manifeste du MSI examinÃ© ; ne pas l'ajouter silencieusement au paquet. Une future redistribution de FFmpeg nÃ©cessiterait une revue distincte de sa configuration et de ses sources.

## DÃ©cision et limites

Publication du code prÃ©parÃ©e sous GPL-3.0-or-later avec les notices tierces conservÃ©es. Le MSI existant est accompagnÃ© des notices complÃ©mentaires et de l'archive des sources dans le paquet de premiÃ¨re publication. Ne pas publier le MSI seul en perdant ces complÃ©ments. Les notices seront intÃ©grÃ©es automatiquement au prochain build par la copie existante de Licences ; aucune source applicative n'est modifiÃ©e ici.

Les dÃ©clarations de droits sur les Ã©lÃ©ments originaux et l'attribution des trois rÃ´les Ã  tiikonic420 sont confirmÃ©es par le mainteneur. La signature n'est pas activÃ©e et la stabilitÃ© n'est pas autorisÃ©e. La revue n'est ni une garantie juridique ni un contrÃ´le de brevets ou d'exportation. Les conditions particuliÃ¨res des composants systÃ¨me restent applicables Ã  tout redistributeur.

Sources de rÃ©fÃ©rence :

- https://signpath.org/terms.html
- https://docs.python.org/3.13/license.html
- https://www.python.org/ftp/python/3.13.16/python-3.13.16-amd64.exe.spdx.json
- https://github.com/laggykiller/sqlcipher3
- https://github.com/sqlcipher/sqlcipher/blob/v4.12.0/LICENSE.md
- https://github.com/openssl/openssl/blob/openssl-3.5.9/LICENSE.txt
- https://github.com/openssl/openssl/blob/openssl-3.6.0/LICENSE.txt
- https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files

Les journaux Windows, les bibliothÃ¨ques musicales et les preuves privÃ©es du poste ne sont pas des fichiers de release et ne doivent pas Ãªtre publiÃ©s.
