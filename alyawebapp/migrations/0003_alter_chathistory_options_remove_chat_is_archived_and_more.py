# Generated by Django 5.1.5 on 2025-01-31 03:53

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('alyawebapp', '0002_initial_data'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='chathistory',
            options={'ordering': ['created_at']},
        ),
        migrations.RemoveField(
            model_name='chat',
            name='is_archived',
        ),
        migrations.AddField(
            model_name='chat',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='chathistory',
            name='user',
            field=models.ForeignKey(default=2, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='chathistory',
            name='chat',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='alyawebapp.chat'),
        ),
        migrations.AlterField(
            model_name='chathistory',
            name='content',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='chathistory',
            name='is_user',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='userintegration',
            name='access_token',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='userintegration',
            name='config',
            field=models.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name='userintegration',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='userintegration',
            name='refresh_token',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='userintegration',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
