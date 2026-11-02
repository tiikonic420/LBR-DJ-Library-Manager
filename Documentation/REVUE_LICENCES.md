# Revue technique des licences — R10

État au 2 novembre 2026 : revue des 16 distributions Python inventoriées et des composants natifs identifiés dans le MSI SHA256 `86dceabb773f6d8d601b3dcbc56d1dfacf40dead517deb8b4ca87e5fe6a00228`. Aucun moteur, TaskHub, SQLite ou test modifié. Aucun conflit de licence identifié dans les éléments examinés avec l'option GPL-3.0-or-later du code original ; cette conclusion reste limitée à ces fichiers et versions.

| Distribution | Version | Licence / périmètre |
| --- | --- | --- |
| bidict | 0.24.1 | MPL-2.0 |
| construct | 2.10.70 | MIT |
| greenlet | 3.2.4 | MIT AND Python-2.0 |
| mutagen | 1.48.1 | GPL-2.0-or-later |
| numpy | 2.2.6 | BSD-3-Clause + notices incorporées, exception GCC |
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

- Mutagen : texte GPL et archive source 1.48.1 fournis ; GPL-2.0-or-later autorise l'option version 3. rbsync : archive source et licence MIT fournies. bidict : licence MPL-2.0 et code Python en clair livrés ; conserver et rendre disponibles ces sources lors de la redistribution.
- CPython 3.13.16 : licence PSF et licences incorporées fournies. Le SBOM officiel du programme d'installation amont a servi d'inventaire complémentaire, sans être présenté comme le SBOM complet de LBR. Les DLL OpenSSL et SQLCipher du MSI sont identiques par SHA256 à celles du runtime interrogé en mémoire.
- SQLCipher 4.12.0 Community / SQLite 3.51.1 dans sqlcipher3-wheels 0.5.7 : wrapper Zlib, SQLCipher BSD-3-Clause, base SQLite domaine public. Version obtenue par base en mémoire, confirmée par l'amalgamation de l'archive source PyPI vérifiée. Notice BSD SQLCipher ajoutée.
- OpenSSL 3.5.9 pour Python et 3.6.0 lié au module SQLCipher : licences Apache-2.0 officielles ajoutées pour les deux versions. Versions confirmées par le runtime et les chaînes des binaires dont les empreintes sont contrôlées. Les chemins NOTICE et NOTICE.txt des deux tags renvoient 404 ; aucune notice inexistante n'est inventée.
- Expat 2.8.5, zlib 1.3.1 et liblzma/XZ 5.2.5 : versions inventoriées dans le SBOM CPython officiel ; copies des notices officielles ajoutées. liblzma est décrit comme domaine public dans COPYING ; les licences des outils XZ ne sont pas appliquées automatiquement à la seule bibliothèque.
- Tcl/Tk 8.6 : notices déjà présentes dans Python.txt et le runtime. libffi, bzip2 et composants Python incorporés : notices Python conservées.
- NumPy 2.2.6 : conserver la notice intégrale incluant OpenBLAS, LAPACK et l'exception d'exécution GCC. Ne pas prétendre que tout NumPy est sous GPL ni retirer l'exception.
- Pillow 12.3.0 : conserver la notice intégrale, qui comporte les notices de ses bibliothèques incorporées, notamment FreeType, JPEG, AVIF, WebP et Brotli ; attribution FreeType ajoutée aux documents de redistribution.
- pip 26.2.1 : ses notices et celles des dépendances vendues sont présentes dans le runtime. Leur licence n'est pas réduite à celle du seul outil pip.
- vcruntime140, vcruntime140_1 et msvcp140 de NumPy : bibliothèques d'exécution système Microsoft, distinctes du code GPL LBR. Les conditions de redistribution Windows s'appliquent ; les avis ne doivent pas être supprimés. Aucun droit de signature de ces DLL n'est revendiqué.
- FFmpeg 9.0.2 : outil des tests CI, absent du manifeste du MSI examiné ; ne pas l'ajouter silencieusement au paquet. Une future redistribution de FFmpeg nécessiterait une revue distincte de sa configuration et de ses sources.

## Décision et limites

Publication du code préparée sous GPL-3.0-or-later avec les notices tierces conservées. Le MSI existant est accompagné des notices complémentaires et de l'archive des sources dans le paquet de première publication. Ne pas publier le MSI seul en perdant ces compléments. Les notices seront intégrées automatiquement au prochain build par la copie existante de Licences ; aucune source applicative n'est modifiée ici.

Les déclarations de droits sur les éléments originaux et l'attribution des trois rôles à tiikonic420 sont confirmées par le mainteneur. La signature n'est pas activée et la stabilité n'est pas autorisée. La revue n'est ni une garantie juridique ni un contrôle de brevets ou d'exportation. Les conditions particulières des composants système restent applicables à tout redistributeur.

Sources de référence :

- https://signpath.org/terms.html
- https://docs.python.org/3.13/license.html
- https://www.python.org/ftp/python/3.13.16/python-3.13.16-amd64.exe.spdx.json
- https://github.com/laggykiller/sqlcipher3
- https://github.com/sqlcipher/sqlcipher/blob/v4.12.0/LICENSE.md
- https://github.com/openssl/openssl/blob/openssl-3.5.9/LICENSE.txt
- https://github.com/openssl/openssl/blob/openssl-3.6.0/LICENSE.txt
- https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files

Les journaux Windows, les bibliothèques musicales et les preuves privées du poste ne sont pas des fichiers de release et ne doivent pas être publiés.
