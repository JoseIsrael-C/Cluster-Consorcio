from django.contrib import admin
from django.utils import timezone
from .models import ct_perfil,ct_modulos,User, tb_usaurios, Aspirante #tb_usaurios
from simple_history.admin import SimpleHistoryAdmin


# Register your models here.
#admin.site.register(tb_usaurios)
admin.site.register(ct_modulos)
admin.site.register(ct_perfil)
#admin.site.register

@admin.register(tb_usaurios)
class tb_usauriosAdmin(SimpleHistoryAdmin):
    list_display = ("id", "telefono", "whatsapp", "registro", "borrado")


@admin.register(Aspirante)
class AspiranteAdmin(admin.ModelAdmin):
    list_display = ("nombre_completo", "email", "estado", "fecha_creacion", "usuario_asignado", "borrado")
    search_fields = ("nombre", "apellidos", "email", "curp")
    list_filter = ("estado", "fecha_creacion", "borrado")
    readonly_fields = ("fecha_creacion", "fecha_ultima_revision")
    fieldsets = (
        ('Información Personal', {
            'fields': ('nombre', 'apellidos', 'email', 'telefono', 'curp')
        }),
        ('Gestión', {
            'fields': ('estado', 'observaciones', 'usuario_asignado')
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_ultima_revision', 'borrado'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['marcar_en_revision', 'marcar_aceptado', 'marcar_rechazado']
    
    def marcar_en_revision(self, request, queryset):
        updated = queryset.update(estado='en_revision', fecha_ultima_revision=timezone.now())
        self.message_user(request, f'{updated} aspirante(s) marcado(s) en revisión.')
    marcar_en_revision.short_description = "Marcar como En Revisión"
    
    def marcar_aceptado(self, request, queryset):
        updated = queryset.update(estado='aceptado', fecha_ultima_revision=timezone.now())
        self.message_user(request, f'{updated} aspirante(s) marcado(s) como aceptado(s).')
    marcar_aceptado.short_description = "Marcar como Aceptado"
    
    def marcar_rechazado(self, request, queryset):
        updated = queryset.update(estado='rechazado', fecha_ultima_revision=timezone.now())
        self.message_user(request, f'{updated} aspirante(s) marcado(s) como rechazado(s).')
    marcar_rechazado.short_description = "Marcar como Rechazado"
