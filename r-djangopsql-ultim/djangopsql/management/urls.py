from django.urls import path
from . import views

urlpatterns = [
    # URLs de autenticación y home
    path('', views.renderUsaurio, name='homeP'),
    path('signup/', views.loadPageCreateUser, name='signup'),
    path('signin/', views.initSession, name='signin'),
    path('logout/', views.cerrarSession, name='logout'),

    # URLs para Menus (el error viene de aquí)
    path('admin/menus/', views.loadPageMenu, name='pageMenu'),
    path('admin/menus/crear/', views.crearMenu, name='crear_menu'),
    path('admin/menus/crear-submenu/', views.crearSubMenu, name='crear_submenu'),
    path('admin/menus/modulo/eliminar/<int:modulo_id>/', views.eliminar_modulo, name='eliminar_modulo'),
    path('admin/menus/modulo/activar/<int:modulo_id>/', views.activar_modulo, name='activar_modulo'),
    path('admin/menus/submodulo/eliminar/<int:submodulo_id>/', views.eliminar_submodulo, name='eliminar_submodulo'),

    # URLs para Documentos Personales
    path('documentos/', views.listar_documentos, name='listar_documentos'),
    path('documentos/subir/', views.subir_documento, name='subir_documento'),
    path('documentos/subir-personal/', views.subir_documento_personal, name='subir_documento_personal'),
    path('documentos/subir-personal/<int:alumno_id>/', views.subir_documento_personal, name='subir_documento_personal_alumno'),
    path('documentos/editar/<int:documento_id>/', views.editar_documento, name='editar_documento'),
    path('documentos/eliminar/<int:documento_id>/', views.eliminar_documento, name='eliminar_documento'),

    # --- ¡AQUÍ ESTÁN LAS URLS QUE FALTABAN! ---
    path('documentos/gestionar/', views.gestionar_documentos_personales, name='gestionar_documentos_personales'),
    path('documentos/revisar/<int:documento_id>/', views.revisar_documento_personal, name='revisar_documento_personal'),

    # URLs para Cardex Académico (Alumnos, Calificaciones, etc.)
    path('cardex/dashboard/', views.dashboard_cardex, name='dashboard_cardex'),
    path('alumnos/', views.listar_alumnos, name='listar_alumnos'),
    path('alumnos/crear/', views.crear_alumno, name='crear_alumno'),
    path('alumnos/detalle/<int:alumno_id>/', views.detalle_alumno, name='detalle_alumno'),
    path('alumnos/editar/<int:alumno_id>/', views.editar_alumno, name='editar_alumno'),
    path('alumnos/eliminar/<int:alumno_id>/', views.eliminar_alumno, name='eliminar_alumno'),

    path('calificaciones/registrar/', views.registrar_calificacion, name='registrar_calificacion'),
    path('calificaciones/historial/', views.historial_calificaciones, name='historial_calificaciones'),
    path('calificaciones/editar/<int:calificacion_id>/', views.editar_calificacion, name='editar_calificacion'),

    # URLs para Documentos Académicos
    path('documentos-academicos/', views.listar_documentos_academicos, name='listar_documentos_academicos'),
    path('documentos-academicos/subir/', views.subir_documento_academico, name='subir_documento_academico'),
    path('documentos-academicos/subir/<int:alumno_id>/', views.subir_documento_academico, name='subir_documento_academico_alumno'),
    path('documentos-academicos/gestionar/', views.gestionar_documentos_academicos, name='gestionar_documentos_academicos'),
    path('documentos-academicos/revisar/<int:documento_id>/', views.revisar_documento_academico, name='revisar_documento_academico'),
    path('documentos-academicos/editar/<int:documento_id>/', views.editar_documento_academico, name='editar_documento_academico'),
    path('documentos-academicos/eliminar/<int:documento_id>/', views.eliminar_documento_academico, name='eliminar_documento_academico'),

    # URLs para Documentos de Titulación
    path('documentos-titulacion/', views.listar_documentos_titulacion, name='listar_documentos_titulacion'),
    path('documentos-titulacion/subir/', views.subir_documento_titulacion, name='subir_documento_titulacion'),
    path('documentos-titulacion/subir/<int:alumno_id>/', views.subir_documento_titulacion, name='subir_documento_titulacion_alumno'),

    # URLs para Blockchain y Certificados
    path('certificados/', views.emitirCertificado, name='certificados'),
    path('certificados/consultar/', views.consultarCertificado, name='consultar_certificado'),
    path('documentos/emitir-certificado/<int:documento_id>/', views.emitir_certificado_para_documento, name='emitir_certificado_para_documento'),
    path('certificados/verificar/', views.verificar_certificado_blockchain, name='verificar_certificado_blockchain'),
    path('alumnos/hash/<int:alumno_id>/', views.generar_hash_alumno, name='generar_hash_alumno'),
    path('documentos/certificado/<int:documento_id>/<str:tipo_documento>/', views.generar_certificado_documento, name='generar_certificado_documento'),
    path('documentos/ver-certificado/<int:documento_id>/<str:tipo_documento>/', views.ver_certificado_documento, name='ver_certificado_documento'),

    # URLs para Administración (Categorías, Carreras, etc.)
    path('admin/catalogos/', views.gestionar_catalogos, name='ct_catalogos'),
    path('admin/documentos-unificados/', views.gestionar_documentos_unificado, name='gestionar_documentos_unificado'),
    path('admin/perfiles/', views.gestionar_perfiles, name='gestionar_perfiles'),
    path('admin/perfiles/desactivar/<int:perfil_id>/', views.desactivar_perfil, name='desactivar_perfil'),
    path('admin/perfiles/permisos/<int:perfil_id>/', views.gestionar_permisos_perfil, name='gestionar_permisos_perfil'),
    path('admin/usuarios/', views.gestionar_usuarios_mejorado, name='gestionar_usuarios'),
    path('admin/usuarios/crear/', views.crear_usuario, name='crear_usuario'),
    path('admin/usuarios/editar/<int:usuario_id>/', views.editar_usuario, name='editar_usuario'),
    path('admin/usuarios/eliminar/<int:usuario_id>/', views.eliminar_usuario, name='eliminar_usuario'),
    path('admin/usuarios/reactivar/<int:usuario_id>/', views.reactivar_usuario, name='reactivar_usuario'),
    path('admin/usuarios/historial/', views.historial_usuarios, name='historial_usuarios'),
    path('admin/usuarios/exportar-csv/', views.exportar_usuarios_csv, name='exportar_usuarios_csv'),
    path('admin/configurar-cuenta/', views.configurar_cuenta_admin, name='configurar_cuenta_admin'),
    path('admin/usuarios/cambiar-password/<int:usuario_id>/', views.cambiar_password_usuario, name='cambiar_password_usuario'),
    path('admin/mi-perfil/', views.ver_perfil_admin, name='ver_perfil_admin'),
    path('admin/categorias-documentos/', views.gestionar_categorias_documentos, name='gestionar_categorias_documentos'),
    path('admin/carreras/', views.gestionar_carreras_admin, name='gestionar_carreras_admin'),
    path('admin/carreras/desactivar/<int:carrera_id>/', views.desactivar_carrera, name='desactivar_carrera'),
    path('admin/carreras/activar/<int:carrera_id>/', views.activar_carrera, name='activar_carrera'),
    path('admin/carreras/eliminar/<int:carrera_id>/', views.eliminar_carrera, name='eliminar_carrera'),
    path('admin/materias/', views.gestionar_materias, name='gestionar_materias'),
    path('admin/instituciones/', views.gestionar_instituciones_procedencia, name='gestionar_instituciones_procedencia'),

    # URLs para AJAX
    path('ajax/filtrar-materias/', views.filtrar_materias_por_carrera, name='filtrar_materias_por_carrera'),
    # Panel Jefatura
    path('jefatura/panel/', views.jefatura_panel, name='jefatura_panel'),
    path('jefatura/alumnos/', views.jefatura_lista_alumnos, name='jefatura_lista_alumnos'),
    path('control-escolar/panel/', views.control_escolar_panel, name='control_escolar_panel'),
    path('profesor/panel/', views.profesor_panel, name='profesor_panel'),

    # URLs para Aspirantes (acceso sin cuenta)
    path('aspirante/ingreso/', views.ingreso_aspirante, name='ingreso_aspirante'),
    path('aspirante/subir-documento/', views.subir_documento_aspirante, name='subir_documento_aspirante'),
    path('aspirante/mis-documentos/', views.documentos_aspirante, name='documentos_aspirante'),
    path('aspirante/cerrar-sesion/', views.cerrar_sesion_aspirante, name='cerrar_sesion_aspirante'),

    # URLs para Gestión de Aspirantes (Admin)
    path('admin/aspirantes/', views.gestionar_aspirantes, name='gestionar_aspirantes'),
    path('admin/aspirantes/<int:aspirante_id>/', views.detalle_aspirante, name='detalle_aspirante'),
    path('admin/aspirantes/<int:aspirante_id>/editar/', views.editar_aspirante, name='editar_aspirante'),
    path('admin/aspirantes/<int:aspirante_id>/eliminar/', views.eliminar_aspirante, name='eliminar_aspirante'),
    path('admin/aspirantes/asignar-revisores/', views.asignar_revisores_aspirantes, name='asignar_revisores_aspirantes'),
    
    # URLs para Gestión de Documentos de Aspirantes
    path('admin/documentos-aspirante/<int:documento_id>/aprobar/', views.aprobar_documento_aspirante, name='aprobar_documento_aspirante'),
    path('admin/documentos-aspirante/<int:documento_id>/rechazar/', views.rechazar_documento_aspirante, name='rechazar_documento_aspirante'),
]