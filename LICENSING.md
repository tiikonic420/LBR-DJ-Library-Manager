# Licences et redistribution

## Éléments propres à LBR

Les éléments originaux de LBR DJ Library Manager sont distribués sous GNU GPL version 3 ou, au choix du destinataire, toute version ultérieure (`GPL-3.0-or-later`). Le texte intégral est dans LICENSE et Licences/LBR-GPL-3.0.txt. Le mainteneur tiikonic420 a confirmé cette autorisation, à sa connaissance, le 2 novembre 2026. La portée couvre ses contributions originales, les scripts, tests, références de non-régression et images propres à LBR, dans la mesure des droits qu'il peut accorder. Elle n'étend pas ces droits aux éléments tiers ou marques.

Le projet a été développé avec assistance GPT. Cette mention ne garantit pas l'exclusivité ou la protection par droit d'auteur de chaque sortie générée. La déclaration du mainteneur et les notices existantes sont conservées.

## Composants tiers

Ils conservent leurs licences et auteurs. Le détail des versions, licences et obligations est dans Documentation/REVUE_LICENCES.md. Les notices sont dans Licences et dans le runtime distribué. Mutagen est GPL-2.0-or-later, utilisable sous GPLv3 pour cette combinaison ; bidict conserve MPL-2.0 et ses sources Python sont livrées. Ni MPL ni GPL ne sont remplacées par une simple mention MIT.

Python, Tcl/Tk, SQLite, SQLCipher, OpenSSL, NumPy, Pillow et leurs composants incorporés conservent leurs licences propres. L'exception GCC présente dans NumPy reste propre aux composants auxquels elle s'applique ; elle ne devient pas une exception générale à la GPL de LBR. Cette distribution utilise FreeType (https://freetype.org), OpenSSL (https://openssl.org), SQLCipher de Zetetic et du code XZ Utils (https://tukaani.org/xz/).

Les composants d'exécution Microsoft sont des bibliothèques système pour Windows, non du code LBR sous GPL. Conserver leurs avis et conditions propres, notamment l'avis Microsoft du runtime Python. Ne pas altérer leurs mentions, les utiliser pour un autre système, ni présenter les produits comme approuvés par Microsoft. Les restrictions propres à ces composants ne restreignent pas les droits GPL sur le code LBR. Le périmètre de signature SignPath ne comprend pas ces DLL ni les binaires tiers.

## Fourniture des sources

Publier l'archive de sources et les scripts de construction avec chaque paquet binaire, depuis la même page de release, sans surcoût. La release décrit le commit réellement compilé ; les ajouts documentaires ne doivent pas être présentés comme une reconstruction. Les sources Mutagen et rbsync sont fournies dans Licences ; les modules Python purs, dont bidict, sont également livrés dans le runtime. Le dépôt donne le code du lanceur C# et les scripts nécessaires. Conserver les avis de modifications et toutes les notices tierces lors de toute redistribution.

Le MSI GitHub déjà testé n'intègre pas les ajouts de notices effectués après sa construction. Pour cette première publication, il doit être distribué uniquement dans le paquet complet fourni, avec notices et sources accessibles à ses côtés. La prochaine construction intégrera ces ajouts via le répertoire Licences déjà copié par le build. Une version signée devra être reconstruite, identifiée et retestée.

Ce document est le résultat d'une revue technique des fichiers et des textes de licences ; il ne constitue pas une attestation juridique universelle. Tout ajout ou changement de dépendance exige une nouvelle revue.
