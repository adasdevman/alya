from django.db import migrations

def add_integrations(apps, schema_editor):
    Integration = apps.get_model('alyawebapp', 'Integration')
    Domain = apps.get_model('alyawebapp', 'Domain')
    
    # Créer ou récupérer le domaine Communication
    communication_domain, _ = Domain.objects.get_or_create(
        name='Communication'
    )
    
    # Créer l'intégration Gmail
    Integration.objects.get_or_create(
        name='Gmail',
        defaults={
            'domain': communication_domain,
            'icon_class': 'fa fa-envelope'
        }
    )
    
    # Créer l'intégration Slack
    Integration.objects.get_or_create(
        name='Slack',
        defaults={
            'domain': communication_domain,
            'icon_class': 'fab fa-slack'
        }
    )

    # Créer l'intégration Google Drive
    Integration.objects.get_or_create(
        name='Google Drive',
        defaults={
            'domain': communication_domain,
            'icon_class': 'fab fa-google-drive'
        }
    )

def remove_integrations(apps, schema_editor):
    Integration = apps.get_model('alyawebapp', 'Integration')
    Integration.objects.filter(name__in=['Gmail', 'Slack', 'Google Drive']).delete()

class Migration(migrations.Migration):
    dependencies = [
        ('alyawebapp', '0006_chat_is_active_chat_title_alter_integration_name'),
    ]

    operations = [
        migrations.RunPython(add_integrations, remove_integrations),
    ] 