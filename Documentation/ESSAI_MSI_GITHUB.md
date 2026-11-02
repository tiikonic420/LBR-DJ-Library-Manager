# Essai du MSI GitHub R10 â€” 2 novembre 2026

Statut : RC non signÃ©e maintenue. Aucun changement applicatif pour ces essais. DÃ©pÃ´t privÃ©, aucune candidature SignPath envoyÃ©e.

## Paquet identifiÃ©

- Commit compilÃ© : `9881a5bc1eac1480d431b405745a09fbcb03bd95`.
- Run : https://github.com/tiikonic420/LBR-DJ-Library-Manager/actions/runs/41406418487 (privÃ©).
- SHA256 du MSI testÃ© : `86dceabb773f6d8d601b3dcbc56d1dfacf40dead517deb8b4ca87e5fe6a00228`.
- 5 605 fichiers ; MSI 5.0.10 ; lanceur 5.0.10.1. Les changements documentaires ultÃ©rieurs ne reconstruisent pas ce paquet.

## RÃ©ussites sur le PC Windows du mainteneur

L'utilisateur confirme l'installation, le lancement du programme installÃ© via un profil fictif, le glisser-dÃ©poser des deux WAV synthÃ©tiques, l'enregistrement du titre sur Essai_A.wav, la vÃ©rification d'intÃ©gritÃ© par interface et la restauration. Les contrÃ´les automatiques confirment les 5 605 empreintes avant lancement, les deux WAV restaurÃ©s Ã  l'identique, six sauvegardes dont les blocs correspondent aux SHA256 de leurs manifestes, une fermeture avec code 0, aucune trace Python dans le journal applicatif et aucun cache pyc dans le rÃ©pertoire installÃ©.

L'utilisateur confirme la dÃ©sinstallation Windows. Le rÃ©pertoire d'installation et les trois raccourcis contrÃ´lÃ©s ont disparu. Les 23 fichiers fictifs relevÃ©s avant dÃ©sinstallation sont encore prÃ©sents avec exactement les mÃªmes empreintes, sauvegardes comprises. Ces constats portent sur ces chemins et ne constituent pas un audit de tous les rÃ©sidus possibles du registre ou du PC.

## Windows Sandbox : rÃ©ussites et blocage

Installation et dÃ©sinstallation Windows Installer : codes 0. Les 5 605 empreintes et les cibles des raccourcis sont conformes. Une sauvegarde/restauration synthÃ©tique via les modules installÃ©s rÃ©ussit, avec chemin accentuÃ© et conservation des six fichiers du profil fictif aprÃ¨s dÃ©sinstallation.

L'unique tentative du lanceur installÃ© est bloquÃ©e par le contrÃ´le d'application Windows, erreur 4551. Les Ã©vÃ©nements collectÃ©s montrent les politiques VerifiedAndReputableDesktop prÃ©sentes ; le relevÃ© de cette campagne ne contient pas d'Ã©vÃ©nement 3077 nommant LBR, et n'identifie donc pas Ã  lui seul une rÃ¨gle spÃ©cifique au fichier. Les journaux bruts sont conservÃ©s localement. Aucun nouvel essai de lancement dans Sandbox, aucune protection dÃ©sactivÃ©e et aucun lancement alternatif de la GUI par Python.

Non exÃ©cutÃ©s dans Sandbox : GUI, glisser-dÃ©poser manuel, sauvegarde/restauration par interface et mutex du paquet installÃ©. La rÃ©ussite sur le PC hÃ´te ne valide pas ces points dans Sandbox.

## Incident de l'outil d'essai conservÃ©

AprÃ¨s une premiÃ¨re restauration, un nouvel enregistrement fictif a modifiÃ© Essai_A.wav. Relancer le scÃ©nario initial, qui attendait des fichiers vierges, a provoquÃ© son arrÃªt de contrÃ´le avant lancement de LBR. Le journal et le premier rÃ©sultat non restaurÃ© sont conservÃ©s. Un lanceur de reprise distinct a ensuite vÃ©rifiÃ© le nouvel Ã©tat exact enregistrÃ© ainsi que sa sauvegarde originale, puis permis le parcours de restauration. Aucun WAV ni sauvegarde n'a Ã©tÃ© rÃ©initialisÃ© par l'outil. Le rÃ©sultat final confirme les originaux Ã  l'identique.

## ContrÃ´les ouverts

- Signature reconnue, reconstruction avec lanceur signÃ©, signature MSI et nouveaux manifestes ; refaire les essais Windows et Sandbox sur ces nouveaux octets.
- Validation MSI ICE exhaustive non exÃ©cutÃ©e.
- RÃ©ouverture/synchronisations dans Rekordbox et Serato avec bibliothÃ¨ques exclusivement fictives non exÃ©cutÃ©es.
- MFA GitHub et droits de publication des Ã©lÃ©ments originaux confirmÃ©s par le mainteneur le 2 novembre 2026 : dÃ©clarations, sans vÃ©rification indÃ©pendante des droits. Licences tierces conservÃ©es ; qualification finale des redistributions tierces et rÃ´les de signature Ã  finaliser.
- Pour SignPath : liens actuellement privÃ©s, aucune release publique ni rÃ©putation publique Ã©tablie revendiquÃ©e. Publication Ã©ventuelle et dÃ©pÃ´t de candidature attendent une instruction distincte ; admission non garantie.

Les journaux Windows bruts, chemins du PC et fichiers d'essai restent dans le dossier de preuves local, hors dÃ©pÃ´t. Les moteurs, TaskHub, SQLite, les tests et leurs assertions sont inchangÃ©s. Aucun accÃ¨s aux bibliothÃ¨ques musicales personnelles dans ce parcours.

## Revue prÃ©alable Ã  la publication â€” 2 novembre 2026

Les trois rÃ´les sont confirmÃ©s pour tiikonic420 : committer, relecteur et approbateur manuel. La revue technique des licences est consignÃ©e dans REVUE_LICENCES.md. Les notices complÃ©mentaires SQLCipher, OpenSSL, Expat, zlib et XZ ainsi que GPL LBR sont ajoutÃ©es aux sources ; elles ne modifient pas le MSI dÃ©jÃ  compilÃ©. Publier le paquet complet accompagnÃ© de ces notices et des sources. Le dÃ©pÃ´t reste privÃ© jusquâ€™Ã  lâ€™Ã©tape de publication rÃ©alisÃ©e par son propriÃ©taire. Aucune demande SignPath envoyÃ©e.
