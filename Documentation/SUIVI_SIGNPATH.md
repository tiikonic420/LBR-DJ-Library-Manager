# Suivi de la demande SignPath — 2 novembre 2026

La préversion [5.0 RC R10 non signée](https://github.com/tiikonic420/LBR-DJ-Library-Manager/releases/tag/v5.0.0-rc10) est publique. Ses quatre fichiers ont été téléchargés sans authentification et comparés par SHA256 aux fichiers préparés ; les deux ZIP ont également été contrôlés sans erreur d'intégrité.

La demande gratuite SignPath a été renseignée avec les liens publics, les résultats réels et l'absence de réputation publique établie revendiquée. Le mainteneur a explicitement accepté les conditions et le traitement des données nécessaires. Les deux cases obligatoires ont été cochées ; l'option de communications commerciales est restée décochée. Un seul clic Submit a été effectué par l'agent ; le CAPTCHA a été terminé par le mainteneur.

Le mainteneur confirme ensuite un message de réception de la demande. Cette preuve est une confirmation du mainteneur : la tentative de relecture de l'onglet par l'agent a échoué avec « browser.user is unavailable ». Aucun numéro de dossier ni accusé reçu par e-mail n'a été consulté indépendamment. L'agent n'a pas réessayé l'envoi et ne revendique pas de deuxième soumission.

**État : demande reçue selon confirmation du mainteneur ; admission SignPath en attente. Aucun certificat obtenu, aucune signature créée et aucune stabilité autorisée.**

Le dépôt et la release décrivent les rôles confirmés : tiikonic420, committer, relecteur des contributions externes et approbateur manuel. MFA GitHub est confirmée par le mainteneur ; MFA et les rôles SignPath devront être configurés si l'accès est accordé.

## Suite

Surveiller la boîte de réception et les indésirables de l'adresse utilisée pour la demande. Conserver l'accusé ou le numéro de dossier s'ils sont fournis. Ne pas envoyer une demande en double. L'admission d'un projet nouvellement publié reste à l'appréciation de SignPath ; aucun délai ou résultat n'est promis.

Si accepté : configurer l'intégration GitHub hébergée et les métadonnées produit/version, signer seulement le lanceur propre à LBR puis le MSI qui le contient, régénérer les manifestes et tester les nouveaux paquets. Les DLL système et bibliothèques tierces ne doivent pas être signées comme des créations LBR.

Restent bloquants pour la stabilité : lancement du paquet signé et parcours GUI dans Sandbox, validation MSI ICE exhaustive et intégrations/réouvertures Rekordbox/Serato sur bibliothèques fictives. Les réussites du MSI non signé restent acquises pour les octets réellement testés ; elles ne valident pas automatiquement un nouveau paquet signé.

Les archives de la release restent inchangées. Les ajouts de suivi concernent uniquement les documents du dépôt ; les moteurs, TaskHub, SQLite et les tests ne sont pas modifiés.
