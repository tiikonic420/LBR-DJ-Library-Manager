# Essai du MSI GitHub R10 — 2 novembre 2026

Statut : RC non signée maintenue. Aucun changement applicatif pour ces essais. Dépôt privé, aucune candidature SignPath envoyée.

## Paquet identifié

- Commit compilé : `9881a5bc1eac1480d431b405745a09fbcb03bd95`.
- Run : https://github.com/tiikonic420/LBR-DJ-Library-Manager/actions/runs/41406418487 (privé).
- SHA256 du MSI testé : `86dceabb773f6d8d601b3dcbc56d1dfacf40dead517deb8b4ca87e5fe6a00228`.
- 5 605 fichiers ; MSI 5.0.10 ; lanceur 5.0.10.1. Les changements documentaires ultérieurs ne reconstruisent pas ce paquet.

## Réussites sur le PC Windows du mainteneur

L'utilisateur confirme l'installation, le lancement du programme installé via un profil fictif, le glisser-déposer des deux WAV synthétiques, l'enregistrement du titre sur Essai_A.wav, la vérification d'intégrité par interface et la restauration. Les contrôles automatiques confirment les 5 605 empreintes avant lancement, les deux WAV restaurés à l'identique, six sauvegardes dont les blocs correspondent aux SHA256 de leurs manifestes, une fermeture avec code 0, aucune trace Python dans le journal applicatif et aucun cache pyc dans le répertoire installé.

L'utilisateur confirme la désinstallation Windows. Le répertoire d'installation et les trois raccourcis contrôlés ont disparu. Les 23 fichiers fictifs relevés avant désinstallation sont encore présents avec exactement les mêmes empreintes, sauvegardes comprises. Ces constats portent sur ces chemins et ne constituent pas un audit de tous les résidus possibles du registre ou du PC.

## Windows Sandbox : réussites et blocage

Installation et désinstallation Windows Installer : codes 0. Les 5 605 empreintes et les cibles des raccourcis sont conformes. Une sauvegarde/restauration synthétique via les modules installés réussit, avec chemin accentué et conservation des six fichiers du profil fictif après désinstallation.

L'unique tentative du lanceur installé est bloquée par le contrôle d'application Windows, erreur 4551. Les événements collectés montrent les politiques VerifiedAndReputableDesktop présentes ; le relevé de cette campagne ne contient pas d'événement 3077 nommant LBR, et n'identifie donc pas à lui seul une règle spécifique au fichier. Les journaux bruts sont conservés localement. Aucun nouvel essai de lancement dans Sandbox, aucune protection désactivée et aucun lancement alternatif de la GUI par Python.

Non exécutés dans Sandbox : GUI, glisser-déposer manuel, sauvegarde/restauration par interface et mutex du paquet installé. La réussite sur le PC hôte ne valide pas ces points dans Sandbox.

## Incident de l'outil d'essai conservé

Après une première restauration, un nouvel enregistrement fictif a modifié Essai_A.wav. Relancer le scénario initial, qui attendait des fichiers vierges, a provoqué son arrêt de contrôle avant lancement de LBR. Le journal et le premier résultat non restauré sont conservés. Un lanceur de reprise distinct a ensuite vérifié le nouvel état exact enregistré ainsi que sa sauvegarde originale, puis permis le parcours de restauration. Aucun WAV ni sauvegarde n'a été réinitialisé par l'outil. Le résultat final confirme les originaux à l'identique.

## Contrôles ouverts

- Signature reconnue, reconstruction avec lanceur signé, signature MSI et nouveaux manifestes ; refaire les essais Windows et Sandbox sur ces nouveaux octets.
- Validation MSI ICE exhaustive non exécutée.
- Réouverture/synchronisations dans Rekordbox et Serato avec bibliothèques exclusivement fictives non exécutées.
- MFA GitHub et droits de publication des éléments originaux confirmés par le mainteneur le 2 novembre 2026 : déclarations, sans vérification indépendante des droits. Licences tierces conservées ; qualification finale des redistributions tierces et rôles de signature à finaliser.
- Pour SignPath : liens actuellement privés, aucune release publique ni réputation publique établie revendiquée. Publication éventuelle et dépôt de candidature attendent une instruction distincte ; admission non garantie.

Les journaux Windows bruts, chemins du PC et fichiers d'essai restent dans le dossier de preuves local, hors dépôt. Les moteurs, TaskHub, SQLite, les tests et leurs assertions sont inchangés. Aucun accès aux bibliothèques musicales personnelles dans ce parcours.
