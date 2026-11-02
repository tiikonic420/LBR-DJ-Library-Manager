# Confidentialité — comportement observé dans les sources R10

L'application traite localement les fichiers et bases choisis. Les préférences, journaux, index et sauvegardes sont enregistrés sur le PC ; ils peuvent contenir des chemins et métadonnées musicales et ne doivent pas être rendus publics avec le code.

Les sources applicatives examinées ne montrent pas de télémétrie envoyant automatiquement des morceaux ou bibliothèques à LBR. Cette inspection statique ne constitue pas une preuve d'absence de tout trafic de chaque dépendance ou du système.

RekordSync propose une installation de rbsync après confirmation explicite : elle utilise pip et télécharge depuis GitHub et les services de paquets Python. Dans LBR, le diagnostic appelle rbsync doctor --offline. Le CLI rbsync lancé directement sans cette option peut vérifier la dernière version via api.github.com ; cette distinction est conservée dans la notice. Ces requêtes transmettent les informations réseau habituelles au service contacté ; le code observé n'y joint pas les morceaux ni leur base.

L'installation des dépendances lors de la construction est également une opération réseau explicite. La demande SignPath et les builds GitHub seront des activités du mainteneur, distinctes du fonctionnement du logiciel sur les bibliothèques.

Conserver uniquement des données fictives dans les tickets et exemples. Les politiques de GitHub, de l'index Python utilisé et des autres services sollicités s'appliquent à leurs propres traitements. Une révision de cette notice sera nécessaire si le comportement réseau change.
