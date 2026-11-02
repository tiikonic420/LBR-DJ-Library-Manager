# Licences et redistribution

## Ã‰lÃ©ments propres Ã  LBR

Les Ã©lÃ©ments originaux de LBR DJ Library Manager sont distribuÃ©s sous GNU GPL version 3 ou, au choix du destinataire, toute version ultÃ©rieure (`GPL-3.0-or-later`). Le texte intÃ©gral est dans LICENSE et Licences/LBR-GPL-3.0.txt. Le mainteneur tiikonic420 a confirmÃ© cette autorisation, Ã  sa connaissance, le 2 novembre 2026. La portÃ©e couvre ses contributions originales, les scripts, tests, rÃ©fÃ©rences de non-rÃ©gression et images propres Ã  LBR, dans la mesure des droits qu'il peut accorder. Elle n'Ã©tend pas ces droits aux Ã©lÃ©ments tiers ou marques.

Le projet a Ã©tÃ© dÃ©veloppÃ© avec assistance GPT. Cette mention ne garantit pas l'exclusivitÃ© ou la protection par droit d'auteur de chaque sortie gÃ©nÃ©rÃ©e. La dÃ©claration du mainteneur et les notices existantes sont conservÃ©es.

## Composants tiers

Ils conservent leurs licences et auteurs. Le dÃ©tail des versions, licences et obligations est dans Documentation/REVUE_LICENCES.md. Les notices sont dans Licences et dans le runtime distribuÃ©. Mutagen est GPL-2.0-or-later, utilisable sous GPLv3 pour cette combinaison ; bidict conserve MPL-2.0 et ses sources Python sont livrÃ©es. Ni MPL ni GPL ne sont remplacÃ©es par une simple mention MIT.

Python, Tcl/Tk, SQLite, SQLCipher, OpenSSL, NumPy, Pillow et leurs composants incorporÃ©s conservent leurs licences propres. L'exception GCC prÃ©sente dans NumPy reste propre aux composants auxquels elle s'applique ; elle ne devient pas une exception gÃ©nÃ©rale Ã  la GPL de LBR. Cette distribution utilise FreeType (https://freetype.org), OpenSSL (https://openssl.org), SQLCipher de Zetetic et du code XZ Utils (https://tukaani.org/xz/).

Les composants d'exÃ©cution Microsoft sont des bibliothÃ¨ques systÃ¨me pour Windows, non du code LBR sous GPL. Conserver leurs avis et conditions propres, notamment l'avis Microsoft du runtime Python. Ne pas altÃ©rer leurs mentions, les utiliser pour un autre systÃ¨me, ni prÃ©senter les produits comme approuvÃ©s par Microsoft. Les restrictions propres Ã  ces composants ne restreignent pas les droits GPL sur le code LBR. Le pÃ©rimÃ¨tre de signature SignPath ne comprend pas ces DLL ni les binaires tiers.

## Fourniture des sources

Publier l'archive de sources et les scripts de construction avec chaque paquet binaire, depuis la mÃªme page de release, sans surcoÃ»t. La release dÃ©crit le commit rÃ©ellement compilÃ© ; les ajouts documentaires ne doivent pas Ãªtre prÃ©sentÃ©s comme une reconstruction. Les sources Mutagen et rbsync sont fournies dans Licences ; les modules Python purs, dont bidict, sont Ã©galement livrÃ©s dans le runtime. Le dÃ©pÃ´t donne le code du lanceur C# et les scripts nÃ©cessaires. Conserver les avis de modifications et toutes les notices tierces lors de toute redistribution.

Le MSI GitHub dÃ©jÃ  testÃ© n'intÃ¨gre pas les ajouts de notices effectuÃ©s aprÃ¨s sa construction. Pour cette premiÃ¨re publication, il doit Ãªtre distribuÃ© uniquement dans le paquet complet fourni, avec notices et sources accessibles Ã  ses cÃ´tÃ©s. La prochaine construction intÃ©grera ces ajouts via le rÃ©pertoire Licences dÃ©jÃ  copiÃ© par le build. Une version signÃ©e devra Ãªtre reconstruite, identifiÃ©e et retestÃ©e.

Ce document est le rÃ©sultat d'une revue technique des fichiers et des textes de licences ; il ne constitue pas une attestation juridique universelle. Tout ajout ou changement de dÃ©pendance exige une nouvelle revue.
