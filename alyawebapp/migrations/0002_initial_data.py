from django.db import migrations

def add_initial_data(apps, schema_editor):
    Domain = apps.get_model('alyawebapp', 'Domain')
    BusinessObjective = apps.get_model('alyawebapp', 'BusinessObjective')
    CompanySize = apps.get_model('alyawebapp', 'CompanySize')
    Integration = apps.get_model('alyawebapp', 'Integration')

    # Domains
    domains = {
        'RH': 'fas fa-users',
        'Marketing': 'fas fa-bullhorn',
        'CRM': 'fas fa-address-book',
        'Finance': 'fas fa-chart-line',
        'Analytics': 'fas fa-chart-bar',
        'Support': 'fas fa-headset',
        'Legal': 'fas fa-balance-scale',
        'Logistique': 'fas fa-truck-moving',
        'Projet': 'fas fa-tasks'
    }
    
    domain_objects = {}
    for name, icon in domains.items():
        domain_objects[name] = Domain.objects.create(name=name, icon=icon)

    # Business Objectives
    objectives = [
        ('Augmenter les ventes', 'fas fa-chart-line'),
        ('Réduire les coûts', 'fas fa-piggy-bank'),
        ('Améliorer la satisfaction client', 'fas fa-smile'),
        ('Optimiser les processus', 'fas fa-cogs'),
        ('Développer la marque', 'fas fa-bullseye')
    ]
    
    for name, icon in objectives:
        BusinessObjective.objects.create(name=name, icon=icon)

    # Company Sizes
    sizes = [
        ('1-10 employés', 'XS'),
        ('11-50 employés', 'S'),
        ('51-200 employés', 'M'),
        ('201-1000 employés', 'L'),
        ('1000+ employés', 'XL')
    ]
    
    for label, value in sizes:
        CompanySize.objects.create(label=label, value=value)

    # Integrations
    integrations_data = [
        # RH
        ('LinkedIn Recruiter', 'RH', 'fas fa-linkedin', 'Recrutement et gestion des talents'),
        ('Workday', 'RH', 'fas fa-calendar-alt', 'Gestion RH complète'),
        ('BambooHR', 'RH', 'fas fa-tree', 'Gestion des ressources humaines'),
        
        # Marketing
        ('HubSpot Marketing', 'Marketing', 'fab fa-hubspot', 'Marketing automation'),
        ('Mailchimp', 'Marketing', 'fas fa-envelope', 'Email marketing'),
        ('Google Ads', 'Marketing', 'fab fa-google', 'Publicité en ligne'),
        
        # CRM
        ('HubSpot', 'CRM', 'fab fa-hubspot', 'Plateforme CRM complète'),
        ('Salesforce', 'CRM', 'fas fa-cloud', 'Solution CRM complète'),
        ('Zoho CRM', 'CRM', 'fas fa-users-cog', 'Solution CRM intégrée'),
        
        # Finance
        ('QuickBooks', 'Finance', 'fas fa-book', 'Comptabilité'),
        ('Xero', 'Finance', 'fas fa-calculator', 'Gestion financière'),
        ('Stripe', 'Finance', 'fas fa-credit-card', 'Paiements en ligne'),
        
        # Analytics
        ('Google Analytics', 'Analytics', 'fab fa-google', 'Analyse web'),
        ('Mixpanel', 'Analytics', 'fas fa-chart-pie', 'Analyse produit'),
        ('Amplitude', 'Analytics', 'fas fa-wave-square', 'Analytics produit'),
        
        # Support
        ('Zendesk', 'Support', 'fas fa-headset', 'Service client et support omnicanal'),
        ('Freshdesk', 'Support', 'fas fa-ticket-alt', 'Gestion du support client'),
        ('Intercom', 'Support', 'far fa-comment-dots', 'Messagerie et support client'),
        
        # Legal
        ('DocuSign', 'Legal', 'fas fa-file-signature', 'Signature électronique de documents'),
        ('Clio', 'Legal', 'fas fa-balance-scale', 'Gestion de cabinet juridique'),
        ('LexisNexis', 'Legal', 'fas fa-gavel', 'Base de données juridique'),
        
        # Logistique
        ('ShipStation', 'Logistique', 'fas fa-shipping-fast', 'Gestion des expéditions e-commerce'),
        ('Freightview', 'Logistique', 'fas fa-truck', 'Gestion du transport de marchandises'),
        ('Odoo', 'Logistique', 'fas fa-boxes', 'Gestion des stocks et logistique'),

        # Projet
        ('Jira', 'Projet', 'fab fa-jira', 'Gestion de projet agile'),
        ('Trello', 'Projet', 'fab fa-trello', 'Gestion de projet visuelle'),
        ('Asana', 'Projet', 'fas fa-tasks', 'Gestion de projet collaborative')
    ]

    for name, domain_name, icon_class, description in integrations_data:
        domain = domain_objects.get(domain_name)
        if domain:
            Integration.objects.create(
                name=name,
                domain=domain,
                icon_class=icon_class,
                description=description
            )

class Migration(migrations.Migration):
    dependencies = [
        ('alyawebapp', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(add_initial_data),
    ] 