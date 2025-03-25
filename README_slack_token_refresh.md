# Système de rafraîchissement automatique des tokens Slack

Ce dossier contient les scripts nécessaires pour gérer le rafraîchissement automatique des tokens d'accès Slack. Comme indiqué dans la [documentation officielle de Slack](https://api.slack.com/authentication/rotation), les tokens d'accès Slack expirent au bout de 12 heures et doivent être rafraîchis régulièrement.

## Contenu du dossier

- `check_and_refresh_slack_tokens.py` - Script principal qui vérifie et rafraîchit les tokens Slack
- `setup_slack_token_refresh_task.py` - Script d'installation qui configure une tâche planifiée
- `update_slack_config.py` - Script pour mettre à jour la configuration des intégrations Slack existantes
- `README_slack_token_refresh.md` - Ce fichier de documentation

## Problématique

Les tokens d'accès Slack expirent après 12 heures d'utilisation. Pour maintenir un accès continu à l'API Slack, nous utilisons un mécanisme de rafraîchissement automatique des tokens. Ce système:

1. Vérifie périodiquement la validité des tokens
2. Rafraîchit automatiquement les tokens avant qu'ils n'expirent
3. Met à jour la base de données avec les nouveaux tokens
4. Enregistre les événements dans des fichiers journaux

## Prérequis

- Python 3.7 ou supérieur
- Accès à la base de données de l'application
- Variables d'environnement configurées:
  - `DATABASE_URL` ou `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- Permissions suffisantes pour créer des tâches planifiées (droits administrateur sous Windows)

## Installation

### 1. Test initial

Avant de configurer la tâche planifiée, il est recommandé de tester le script:

```bash
python setup_slack_token_refresh_task.py --test
```

Ce test exécutera le script de rafraîchissement une fois et vérifiera qu'il fonctionne correctement.

### 2. Configuration avec l'intervalle par défaut (4 heures)

```bash
python setup_slack_token_refresh_task.py
```

### 3. Configuration avec un intervalle personnalisé

```bash
python setup_slack_token_refresh_task.py --interval 6
```

Ceci configurera le script pour s'exécuter toutes les 6 heures.

## Configuration sous Windows

Sous Windows, le script crée une tâche dans le Planificateur de tâches. Vous pouvez vérifier la tâche en ouvrant le Planificateur de tâches et en cherchant "SlackTokenRefresh".

## Configuration sous Linux

Sous Linux, le script ajoute une tâche cron. Vous pouvez vérifier la tâche en exécutant:

```bash
crontab -l
```

## Mise à jour des intégrations existantes

Si vous avez des intégrations Slack existantes qui n'ont pas les champs requis pour le rafraîchissement (client_id, client_secret), vous pouvez les mettre à jour avec:

```bash
python update_slack_config.py
```

## Fichiers journaux

Les journaux sont stockés dans les fichiers suivants:
- `slack_token_refresh.log` - Journal du script de rafraîchissement
- `slack_setup.log` - Journal du script d'installation
- `slack_refresh.log` - Journal des exécutions périodiques (stdout/stderr)

## Dépannage

### Le script échoue avec "Erreur de connexion à la base de données"

Vérifiez que les variables d'environnement sont correctement configurées. Vous pouvez les définir temporairement avant d'exécuter le script:

```bash
export DATABASE_URL="postgresql://user:password@host:port/dbname"
python check_and_refresh_slack_tokens.py
```

### Le rafraîchissement des tokens échoue

Vérifiez les journaux pour identifier l'erreur. Les causes les plus courantes sont:
- Refresh token révoqué ou invalide
- Client ID ou Client Secret incorrects
- Problèmes réseau ou API Slack indisponible

### La tâche planifiée ne s'exécute pas

- **Windows**: Vérifiez le Planificateur de tâches et assurez-vous que la tâche est activée
- **Linux**: Vérifiez que le cron daemon est en cours d'exécution avec `systemctl status cron`

## Fonctionnement technique

1. Le script vérifie la base de données pour toutes les intégrations Slack activées
2. Pour chaque intégration, il vérifie si le token est près d'expirer ou invalide
3. Si nécessaire, il utilise le refresh token pour obtenir un nouveau token d'accès
4. Il met à jour la base de données avec les nouveaux tokens et date d'expiration
5. Les erreurs et réussites sont enregistrées dans les fichiers journaux

## Format des tokens

Selon la documentation Slack, les nouveaux tokens ont généralement un préfixe "xoxe.", par exemple "xoxe.xoxb-1234...". Le script est compatible avec ce format et détecte automatiquement le type de token.

## Sécurité

Les client_id et client_secret ne sont jamais journalisés. Les tokens sont tronqués dans les journaux pour éviter les fuites d'informations sensibles.

## Contributions

Pour contribuer à l'amélioration de ce système:
1. Testez vos modifications localement
2. Assurez-vous que tous les tests passent
3. Soumettez une pull request avec une description claire des changements 