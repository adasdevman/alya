from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
import logging
from django.core.exceptions import ValidationError
from .integrations.config import INTEGRATION_CONFIGS

logger = logging.getLogger(__name__)

class CustomUser(AbstractUser):
    is_admin = models.BooleanField(default=False)
    is_moderator = models.BooleanField(default=False)
    company_size = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return self.username

class Domain(models.Model):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50)
    users = models.ManyToManyField(CustomUser, related_name='domains', blank=True)

    def __str__(self):
        return self.name

class BusinessObjective(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='fas fa-bullseye')

    def __str__(self):
        return self.name

class CompanySize(models.Model):
    label = models.CharField(max_length=100)
    value = models.CharField(max_length=50)

    def __str__(self):
        return self.label

class UserProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    domains = models.ManyToManyField(Domain, blank=True)
    business_objectives = models.ManyToManyField(BusinessObjective, blank=True)
    onboarding_complete = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username

class UserDomain(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE)
    selected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'domain')

class Chat(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_archived = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']

class Prompt(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, null=True)
    question = models.TextField()
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.username} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

class Interaction(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)
    interaction_type = models.CharField(max_length=50, default='view')
    details = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.username} - {self.domain.name if self.domain else 'No Domain'} - {self.interaction_type}"

@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=CustomUser)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

class ChatHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    prompt = models.TextField()
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Chat histories'

    def __str__(self):
        return f"{self.user.username} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

class Integration(models.Model):
    name = models.CharField(max_length=100)
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE)
    icon_class = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.name} ({self.domain.name})"

    class Meta:
        ordering = ['name']

class UserIntegration(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    integration = models.ForeignKey(Integration, on_delete=models.CASCADE)
    enabled = models.BooleanField(default=False)
    config = models.JSONField(default=dict, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        unique_together = ('user', 'integration')

    def clean(self):
        if self.enabled:
            config_template = INTEGRATION_CONFIGS.get(self.integration.name.lower(), {})
            if not config_template.get('optional_config', False):
                required_fields = [
                    field['name'] for field in config_template.get('fields', [])
                    if field.get('required', False)
                ]
                missing_fields = [
                    field for field in required_fields 
                    if not self.config or not self.config.get(field)
                ]
                if missing_fields:
                    missing_field_labels = [
                        next(f['label'] for f in config_template['fields'] if f['name'] == field)
                        for field in missing_fields
                    ]
                    raise ValidationError(
                        [f'Champ requis manquant: {label}' for label in missing_field_labels]
                    )

    def save(self, *args, **kwargs):
        if not kwargs.pop('skip_validation', False):
            self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.integration.name}"

@receiver(pre_save, sender=UserIntegration)
def ensure_config_is_dict(sender, instance, **kwargs):
    if not isinstance(instance.config, dict):
        instance.config = {}
    logger.info(f"Sauvegarde de UserIntegration - User: {instance.user.username}, Integration: {instance.integration.name}, Config: {instance.config}")
