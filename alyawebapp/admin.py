from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    CustomUser, 
    Domain, 
    UserProfile, 
    BusinessObjective, 
    CompanySize,
    ChatHistory,
    Interaction,
    UserDomain,
    Integration,
    UserIntegration
)

# Changer le titre de l'administration
admin.site.site_header = "Administration ALYA"
admin.site.site_title = "Administration ALYA"
admin.site.index_title = "ALYA"

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Informations supplémentaires', {'fields': ('company_size',)}),
    )

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Domain)
admin.site.register(UserProfile)
admin.site.register(BusinessObjective)
admin.site.register(CompanySize)
admin.site.register(ChatHistory)
admin.site.register(Interaction)
admin.site.register(UserDomain)

@admin.register(Integration)
class IntegrationAdmin(admin.ModelAdmin):
    list_display = ('name', 'domain', 'icon_class')
    list_filter = ('domain',)
    search_fields = ('name', 'domain__name')
    ordering = ('domain', 'name')

@admin.register(UserIntegration)
class UserIntegrationAdmin(admin.ModelAdmin):
    list_display = ('user', 'integration', 'enabled')
    list_filter = ('enabled', 'integration__domain')
    search_fields = ('user__email', 'integration__name')
    raw_id_fields = ('user', 'integration')
    ordering = ('integration__name',)

    def get_config_display(self, obj):
        return obj.config
    get_config_display.short_description = 'Configuration'

    fieldsets = (
        (None, {
            'fields': ('user', 'integration', 'enabled')
        }),
        ('Configuration', {
            'fields': ('config',),
            'classes': ('collapse',)
        })
    )
