# PrÃ©paration SignPath â€” dÃ©pÃ´t privÃ©

Ã‰tat au 2 novembre 2026 : dÃ©pÃ´t privÃ©, aucune candidature envoyÃ©e, aucun fichier signÃ©, version RC maintenue.

## DÃ©pÃ´t et construction vÃ©rifiÃ©s

- DÃ©pÃ´t : https://github.com/tiikonic420/LBR-DJ-Library-Manager (privÃ©).
- Commit construit : `9881a5bc1eac1480d431b405745a09fbcb03bd95`.
- VÃ©rification GitHub rÃ©ussie : https://github.com/tiikonic420/LBR-DJ-Library-Manager/actions/runs/41406418487.
- 17 suites, 105 cas unittest rÃ©ussis, zÃ©ro ignorÃ©, et 6 scÃ©narios GUI supplÃ©mentaires. Les 7 tests audio passent avec FFmpeg 9.0.2 vÃ©rifiÃ© par SHA256.
- Artefact privÃ© `LBR-R10-unsigned-review-only` : MSI construit depuis les sources, non signÃ©. SHA256 du MSI : `86dceabb773f6d8d601b3dcbc56d1dfacf40dead517deb8b4ca87e5fe6a00228`.
- Les 5 605 fichiers du MSI ont Ã©tÃ© extraits et contrÃ´lÃ©s par SHA256 ; ses 26 fichiers de sources/ressources applicatives correspondent exactement au dÃ©pÃ´t prÃ©parÃ©. Lanceur et Python x64 ; vÃ©rification native MsiVerifyPackage Ã  0 ; aucune action personnalisÃ©e ; table Signature prÃ©sente.
- Les moteurs, TaskHub et SQLite n'ont pas Ã©tÃ© modifiÃ©s. Les changements faits pour la prÃ©paration concernent les documents et les outils CI.

Les ajouts documentaires ultÃ©rieurs ne constituent pas une nouvelle compilation : le lien et le commit ci-dessus identifient exactement les artefacts contrÃ´lÃ©s.

## Ã‰checs et portÃ©e des rÃ©sultats

Le premier essai GitHub, run 41406158325, a Ã©chouÃ© avant les tests LBR dans le script de prÃ©paration FFmpeg (lecture du code retour aprÃ¨s un pipeline interrompu). Le script de CI a Ã©tÃ© corrigÃ© ; le journal initial et celui du succÃ¨s sont conservÃ©s. Aucune assertion produit n'a Ã©tÃ© affaiblie. Les deux cas initialement ignorÃ©s sur le PC local passent aussi dans ce run GitHub ; les anciens journaux de skips ne sont pas effacÃ©s.

Ce MSI CI est une nouvelle compilation : sa documentation et certaines mÃ©tadonnÃ©es de construction diffÃ¨rent du MSI R10 prÃ©cÃ©demment essayÃ© sur Windows 11. Les essais du 2 novembre sont dÃ©taillÃ©s dans ESSAI_MSI_GITHUB.md : parcours GUI rÃ©ussi sur le PC hÃ´te et dÃ©sinstallation avec conservation des 23 fichiers fictifs ; installation/dÃ©sinstallation rÃ©ussies dans Sandbox, mais lancement bloquÃ© par erreur 4551. Le succÃ¨s hÃ´te ne valide pas la GUI dans Sandbox.

L'inventaire du runner trouve darice.cub et smoke.exe WiX 3.14.1, mais pas Msival2. Aucune validation ICE exhaustive n'a Ã©tÃ© exÃ©cutÃ©e. Le programme smoke de WiX 3 supprime ICE33/ICE66 par dÃ©faut ; son existence ne permet pas de dÃ©clarer ces contrÃ´les rÃ©ussis.

## Demande SignPath

Le texte de candidature est dans CANDIDATURE_SIGNPATH.md. Les liens sont encore privÃ©s et ne doivent pas Ãªtre prÃ©sentÃ©s comme des rÃ©fÃ©rences publiques accessibles Ã  SignPath. Ne pas soumettre le formulaire Ã  ce stade.

Le 2 novembre 2026, le propriÃ©taire confirme Ã  sa connaissance les droits de publication du code et des images propres Ã  LBR sous GPL-3.0-or-later, avec conservation des licences tierces, et confirme MFA activÃ©e sur GitHub. Ce sont ses dÃ©clarations, sans audit juridique indÃ©pendant. Avant une Ã©ventuelle demande : finaliser les obligations de redistribution et les rÃ´les de signature, configurer MFA sur SignPath si l'accÃ¨s est accordÃ©, puis obtenir l'instruction explicite du propriÃ©taire pour une ouverture publique et une release RC. Aucun changement de visibilitÃ© n'est autorisÃ© par cette prÃ©paration.

L'admission reste Ã  l'apprÃ©ciation de SignPath, notamment pour la rÃ©putation publique d'un projet nouvellement crÃ©Ã©. Une signature Ã©ventuelle apparaÃ®trait sous le nom du titulaire de leur certificat, SignPath Foundation. Aucun utilisateur, historique public ou soutien externe n'est inventÃ©.

## AprÃ¨s une Ã©ventuelle admission

Qualifier les rÃ¨gles de mÃ©tadonnÃ©es et les artefacts SignPath : signer uniquement le lanceur LBR construit sur GitHub, intÃ©grer celui-ci dans le MSI, signer ensuite le MSI, vÃ©rifier les signatures et actualiser les manifestes/archives. Ne pas signer les binaires Python et bibliothÃ¨ques tierces comme des crÃ©ations LBR. Rejouer les contrÃ´les Windows/Sandbox, ICE et les intÃ©grations DJ fictives avant de discuter une promotion stable.

## Revue prÃ©alable Ã  la publication â€” 2 novembre 2026

Les trois rÃ´les sont confirmÃ©s pour tiikonic420 : committer, relecteur et approbateur manuel. La revue technique des licences est consignÃ©e dans REVUE_LICENCES.md. Les notices complÃ©mentaires SQLCipher, OpenSSL, Expat, zlib et XZ ainsi que GPL LBR sont ajoutÃ©es aux sources ; elles ne modifient pas le MSI dÃ©jÃ  compilÃ©. Publier le paquet complet accompagnÃ© de ces notices et des sources. Le dÃ©pÃ´t reste privÃ© jusquâ€™Ã  lâ€™Ã©tape de publication rÃ©alisÃ©e par son propriÃ©taire. Aucune demande SignPath envoyÃ©e.
