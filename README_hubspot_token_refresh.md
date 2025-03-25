# Rafraîchissement Automatique des Tokens HubSpot

Ce dossier contient des scripts pour gérer automatiquement le rafraîchissement des tokens d'accès HubSpot, évitant ainsi les erreurs d'expiration de token dans votre application.

## Contenu

- `check_and_refresh_hubspot_tokens.py` : Script principal qui vérifie et rafraîchit les tokens HubSpot
- `setup_hubspot_token_refresh_task.py` : Script d'installation qui configure une tâche planifiée
- `README_hubspot_token_refresh.md` : Ce fichier d'aide

## Problème résolu

Les tokens d'accès HubSpot expirent généralement après 30 minutes. Si le token n'est pas rafraîchi à temps, les utilisateurs peuvent rencontrer des erreurs lors de l'utilisation des fonctionnalités liées à HubSpot dans l'application.

Ces scripts mettent en place un système automatisé qui:
1. Vérifie régulièrement si les tokens sont sur le point d'expirer
2. Rafraîchit automatiquement les tokens avant leur expiration
3. Met à jour la base de données avec les nouveaux tokens
4. Enregistre toutes les actions et erreurs dans un fichier journal

## Prérequis

- Python 3.6 ou supérieur
- Accès à la base de données de l'application
- Module `psycopg2` installé (`pip install psycopg2-binary`)
- Droits suffisants pour planifier des tâches sur le système

## Configuration et utilisation

### 1. Test initial

Avant de configurer la tâche planifiée, il est recommandé de tester le script:

```bash
python setup_hubspot_token_refresh_task.py --test
```

Cette commande exécutera le script `check_and_refresh_hubspot_tokens.py` une fois avec l'option `--force` qui force le rafraîchissement des tokens.

### 2. Configuration de la tâche planifiée

#### Sous Windows

```bash
python setup_hubspot_token_refresh_task.py --interval 15
```

Cela créera une tâche planifiée Windows qui exécutera le script toutes les 15 minutes.

Options:
- `--interval` : Intervalle en minutes entre les exécutions (par défaut: 15)
- `--task-name` : Nom de la tâche planifiée (par défaut: "HubSpotTokenRefresh")

Note: Cette commande doit être exécutée avec des privilèges d'administrateur pour pouvoir créer une tâche planifiée.

#### Sous Linux

```bash
python setup_hubspot_token_refresh_task.py --interval 15
```

Cela ajoutera une entrée dans le crontab de l'utilisateur courant pour exécuter le script toutes les 15 minutes.

### 3. Exécution manuelle

Vous pouvez exécuter le script manuellement à tout moment:

```bash
python check_and_refresh_hubspot_tokens.py
```

Options:
- `--force` : Force le rafraîchissement de tous les tokens, même s'ils ne sont pas expirés

## Fichier de log

Toutes les actions et erreurs sont enregistrées dans le fichier `hubspot_token_refresh.log` situé dans le même répertoire que les scripts.

## Fonctionnement technique

Le script `check_and_refresh_hubspot_tokens.py` effectue les opérations suivantes:

1. Se connecte à la base de données
2. Identifie toutes les intégrations HubSpot activées
3. Pour chaque intégration utilisateur:
   - Vérifie si le token est sur le point d'expirer (moins de 30 minutes restantes)
   - Si le token est toujours valide mais expirera bientôt, ou si le token est déjà expiré:
     - Utilise le refresh_token pour obtenir un nouveau token d'accès via l'API HubSpot
     - Met à jour le token dans la base de données
     - Met à jour la date d'expiration
   - Si une erreur survient lors du rafraîchissement:
     - Enregistre l'erreur dans la configuration de l'intégration
     - Évite les tentatives répétées dans un court intervalle

## Dépannage

### Le script ne rafraîchit pas certains tokens

Vérifiez les conditions suivantes:
- L'intégration utilisateur doit être activée
- L'intégration doit avoir un refresh_token, client_id et client_secret valides
- Si une tentative récente a échoué, le script attendra au moins 5 minutes avant de réessayer

### Erreurs d'authentification

Si vous rencontrez des erreurs d'authentification auprès de l'API HubSpot:
1. Vérifiez que les client_id et client_secret sont corrects
2. Vérifiez que le refresh_token n'a pas été révoqué
3. Essayez de régénérer un nouveau refresh_token via le workflow d'authentification OAuth

### Problèmes de connexion à la base de données

Vérifiez que la variable d'environnement `DATABASE_URL` est correctement définie, ou modifiez la valeur par défaut dans le script.

## Personnalisation

Vous pouvez modifier les variables suivantes dans le script:

- `DATABASE_URL` : URL de connexion à la base de données
- Le nom de l'intégration HubSpot (actuellement recherché avec `ILIKE '%hubspot%'`)

## Support

En cas de problème, consultez le fichier journal `hubspot_token_refresh.log` pour des informations détaillées sur les erreurs rencontrées. 