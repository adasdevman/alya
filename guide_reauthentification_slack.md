# Guide de réauthentification de l'intégration Slack

Ce guide vous aidera à réauthentifier votre intégration Slack après une mise à jour des configurations. Cette réauthentification est nécessaire pour générer de nouveaux tokens et assurer le bon fonctionnement de l'intégration.

## Pourquoi réauthentifier ?

Nous avons apporté des améliorations à notre système d'intégration Slack pour permettre un rafraîchissement automatique des tokens d'authentification. Pour que ces améliorations prennent effet, vous devez réauthentifier votre compte Slack une fois.

## Étapes de réauthentification

1. **Connectez-vous à votre compte**
   - Accédez à [votre espace d'administration](https://alya-166a.onrender.com/compte)
   - Connectez-vous avec vos identifiants habituels

2. **Accédez à la page des intégrations**
   - Dans le menu, cliquez sur "Intégrations" ou "Paramètres" > "Intégrations"
   - Localisez l'intégration Slack dans la liste

3. **Désactivez l'intégration existante**
   - Cliquez sur le bouton "Désactiver" à côté de l'intégration Slack
   - Confirmez la désactivation si demandé

4. **Réactivez l'intégration Slack**
   - Cliquez sur "Ajouter une intégration" ou "Configurer" à côté de Slack
   - Suivez les instructions à l'écran pour autoriser l'application
   - Slack vous demandera de confirmer les permissions
   - Cliquez sur "Autoriser"

5. **Vérifiez l'intégration**
   - Après autorisation, vous serez redirigé vers votre application
   - Vérifiez que l'intégration Slack apparaît comme "Activée"
   - Testez l'intégration en envoyant un message test : "Alya, envoie un message sur Slack dans le canal #général : 'Test de réauthentification réussi'"

## Que faire si ça ne fonctionne pas ?

Si vous rencontrez des problèmes après la réauthentification :

1. **Vérifiez les permissions Slack**
   - Assurez-vous que l'application a reçu toutes les permissions nécessaires
   - Si vous n'êtes pas administrateur de l'espace de travail Slack, contactez votre administrateur

2. **Essayez en navigation privée**
   - Certains problèmes peuvent être liés à des cookies ou au cache du navigateur
   - Tentez la réauthentification en mode navigation privée

3. **Contactez l'assistance**
   - Si les problèmes persistent, contactez notre équipe support à [support@example.com](mailto:support@example.com)
   - Précisez que vous avez suivi les étapes de réauthentification Slack

## Avantages de la mise à jour

Cette mise à jour apporte plusieurs avantages :
- **Maintien automatique de la connexion** : Les tokens seront rafraîchis automatiquement avant leur expiration
- **Réduction des erreurs d'authentification** : Moins d'interruptions dans l'utilisation de l'intégration Slack
- **Sécurité améliorée** : Utilisation des meilleures pratiques d'authentification recommandées par Slack

Merci d'avoir pris le temps de mettre à jour votre intégration ! 