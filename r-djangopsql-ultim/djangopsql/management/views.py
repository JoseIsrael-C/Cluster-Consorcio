import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from django.db import transaction
from .models import (ct_perfil, tb_bitacora, ct_modulos, ct_submodulos, ct_puestos, Permiso,
                    MenuList, mainmenu, tb_usaurios, DocumentoPersonal, CategoriaDocumento,
                    Carrera, Alumno, Materia, Calificacion, DocumentoAcademico, InstitucionProcedencia,
                    Aspirante)
# from .serializers import menuserializer, submenuserializer
from datetime import datetime
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.hashers import make_password
from django.db import IntegrityError
from django.urls import reverse
from django.db.models import Count, Sum, F
from django.utils import timezone
from management.forms import CrearMenu, CrearSubMenu
from . import contrato 
import string
import random
import hashlib
from datetime import datetime

def obtener_menu_dinamico(user):
    """
    Genera un menú dinámico basado en el perfil y permisos del usuario.
    Retorna un diccionario con las secciones del menú disponibles.
    """
    menu = {
        'datos_academicos': [],
        'gestion_alumnos': [],
        'documentos': [],
        'seguridad': [],
        'otros': [],
        'mostrarmenu': False,
    }
    
    # Si no está autenticado, retornar menú vacío
    if not user.is_authenticated:
        return menu
    
    # ADMINISTRADORES - Ver todo
    if user.is_superuser:
        menu['mostrarmenu'] = True
        menu['datos_academicos'] = [
            {'nombre': 'Carreras', 'url': 'gestionar_carreras_admin', 'icono': 'fas fa-school', 'color': 'success'},
            {'nombre': 'Materias', 'url': 'gestionar_materias', 'icono': 'fas fa-book', 'color': 'primary'},
            {'nombre': 'Instituciones', 'url': 'gestionar_instituciones_procedencia', 'icono': 'fas fa-map-marker-alt', 'color': 'secondary'},
        ]
        menu['gestion_alumnos'] = [
            {'nombre': 'Alumnos', 'url': 'listar_alumnos', 'icono': 'fas fa-graduation-cap', 'color': 'primary'},
            {'nombre': 'Aspirantes', 'url': 'gestionar_aspirantes', 'icono': 'fas fa-user-check', 'color': 'info'},
            {'nombre': 'Cardex', 'url': 'dashboard_cardex', 'icono': 'fas fa-chart-line', 'color': 'success'},
        ]
        menu['documentos'] = [
            {'nombre': 'Categorías', 'url': 'gestionar_categorias_documentos', 'icono': 'fas fa-folder', 'color': 'primary'},
            {'nombre': 'Gestión Centralizada', 'url': 'gestionar_documentos_unificado', 'icono': 'fas fa-file-upload', 'color': 'info'},
            {'nombre': 'Personales', 'url': 'gestionar_documentos_personales', 'icono': 'fas fa-user-circle', 'color': 'success'},
            {'nombre': 'Académicos', 'url': 'gestionar_documentos_academicos', 'icono': 'fas fa-graduation-cap', 'color': 'warning'},
            {'nombre': 'Titulación', 'url': 'listar_documentos_titulacion', 'icono': 'fas fa-certificate', 'color': 'dark'},
        ]
        menu['seguridad'] = [
            {'nombre': 'Usuarios', 'url': 'gestionar_usuarios', 'icono': 'fas fa-users', 'color': 'danger'},
            {'nombre': 'Perfiles', 'url': 'gestionar_perfiles', 'icono': 'fas fa-user-tag', 'color': 'warning'},
            {'nombre': 'Menús', 'url': 'pageMenu', 'icono': 'fas fa-bars', 'color': 'info'},
        ]
    
    # CONTROL ESCOLAR - Ver datos académicos y documentos
    elif hasattr(user, 'perfil_usuario') and user.perfil_usuario.perfil_fk and user.perfil_usuario.perfil_fk.nombre.lower() == 'control escolar':
        menu['mostrarmenu'] = True
        menu['datos_academicos'] = [
            {'nombre': 'Carreras', 'url': 'gestionar_carreras_admin', 'icono': 'fas fa-school', 'color': 'success'},
            {'nombre': 'Materias', 'url': 'gestionar_materias', 'icono': 'fas fa-book', 'color': 'primary'},
        ]
        menu['documentos'] = [
            {'nombre': 'Gestión Centralizada', 'url': 'gestionar_documentos_unificado', 'icono': 'fas fa-file-upload', 'color': 'info'},
            {'nombre': 'Académicos', 'url': 'gestionar_documentos_academicos', 'icono': 'fas fa-graduation-cap', 'color': 'warning'},
        ]
        menu['otros'] = [
            {'nombre': 'Dashboard', 'url': 'dashboard_cardex', 'icono': 'fas fa-chart-line', 'color': 'info'},
            {'nombre': 'Alumnos', 'url': 'listar_alumnos', 'icono': 'fas fa-users-circle', 'color': 'primary'},
        ]
    
    # PROFESOR - Ver panel y calificaciones
    elif hasattr(user, 'perfil_usuario') and user.perfil_usuario.perfil_fk and user.perfil_usuario.perfil_fk.nombre.lower() == 'profesor':
        menu['mostrarmenu'] = True
        menu['otros'] = [
            {'nombre': 'Mi Panel', 'url': 'profesor_panel', 'icono': 'fas fa-chalkboard-teacher', 'color': 'primary'},
            {'nombre': 'Registrar Calificaciones', 'url': 'registrar_calificacion', 'icono': 'fas fa-edit', 'color': 'warning'},
            {'nombre': 'Historial Calificaciones', 'url': 'historial_calificaciones', 'icono': 'fas fa-list-alt', 'color': 'info'},
        ]
    
    # JEFATURA - Ver panel de jefatura
    elif hasattr(user, 'perfil_usuario') and user.perfil_usuario.perfil_fk and user.perfil_usuario.perfil_fk.nombre.lower() == 'jefatura':
        menu['mostrarmenu'] = True
        menu['otros'] = [
            {'nombre': 'Mi Panel', 'url': 'jefatura_panel', 'icono': 'fas fa-user-tie', 'color': 'primary'},
            {'nombre': 'Alumnos', 'url': 'jefatura_lista_alumnos', 'icono': 'fas fa-users-circle', 'color': 'info'},
        ]
    
    # ALUMNO - Ver documentos personales
    elif hasattr(user, 'perfil_usuario') and user.perfil_usuario.perfil_fk and user.perfil_usuario.perfil_fk.nombre.lower() == 'alumno':
        menu['mostrarmenu'] = True
        menu['documentos'] = [
            {'nombre': 'Mis Documentos Personales', 'url': 'listar_documentos', 'icono': 'fas fa-file-import', 'color': 'success'},
            {'nombre': 'Mis Documentos Académicos', 'url': 'listar_documentos_academicos', 'icono': 'fas fa-graduation-cap', 'color': 'warning'},
        ]
        menu['otros'] = [
            {'nombre': 'Mi Información', 'url': 'detalle_alumno', 'icono': 'fas fa-user-circle', 'color': 'primary'},
        ]
    
    return menu

def obtener_abreviacion_tipo_documento(tipo_documento, documento=None):
    """Función para obtener abreviación del tipo de documento"""
    abreviaciones = {
        # Documentos Académicos
        'certificado': 'CERT',
        'constancia': 'CONST',
        'boleta': 'BOL',
        'historial': 'HIST',
        'titulo': 'TIT',
        'cedula': 'CED',
        'acta_examen': 'ACTA',
        'liberacion_ss': 'LIB_SS',
        'otro': 'OTRO',
        
        # Documentos Personales (por categoría)
        'personal': 'PERS',
        'academico': 'ACAD',
        'admision': 'ADM',
    }
    
    if tipo_documento == 'academico' and documento:
        return abreviaciones.get(documento.tipo_documento, 'ACAD')
    elif tipo_documento == 'personal' and documento:
        # Para documentos personales, usar la categoría
        categoria_nombre = documento.categoria.nombre.lower()
        if 'identificacion' in categoria_nombre or 'ine' in categoria_nombre:
            return 'ID'
        elif 'curp' in categoria_nombre:
            return 'CURP'
        elif 'acta' in categoria_nombre or 'nacimiento' in categoria_nombre:
            return 'ACTA'
        elif 'comprobante' in categoria_nombre:
            return 'COMP'
        elif 'fotografia' in categoria_nombre:
            return 'FOTO'
        else:
            return 'PERS'
    else:
        return abreviaciones.get(tipo_documento, 'DOC')

#usuario
@login_required
def renderUsaurio(request):
    """Vista para la página principal (home) con estadísticas del sistema"""
    # Estadísticas generales
    total_alumnos = Alumno.objects.filter(borrado=1).count()
    total_carreras = Carrera.objects.filter(borrado=1).count()

    # Créditos pendientes (materias no aprobadas)
    creditos_pendientes = Calificacion.objects.filter(
        borrado=1,
        estado__in=['cursando', 'reprobada']
    ).aggregate(total_creditos=Sum('materia__creditos'))['total_creditos'] or 0

    # Documentos subidos hoy
    hoy = timezone.now().date()
    documentos_hoy = DocumentoAcademico.objects.filter(
        borrado=1,
        fecha_subida__date=hoy
    ).count()

    context = {
        'total_alumnos': total_alumnos,
        'total_carreras': total_carreras,
        'creditos_pendientes': creditos_pendientes,
        'documentos_hoy': documentos_hoy,
    }
    return render(request, 'home.html', context)

#crear usuarios
def loadPageCreateUser(request):
    params = {'form': UserCreationForm}  
        
    if request.method == 'GET':
        return render(request, 'signup.html', params)
    else:
        if request.POST['password1'] == request.POST['password2']:
            try:
                objtUser = User.objects.create_user(username=request.POST['username'], 
                                                password=request.POST['password1'])
                objtUser.save()
                login(request, objtUser)
                return redirect('homeP')
            except IntegrityError:
                params = {'form': UserCreationForm, 'error': 'Usuario ya existe'}
                return render(request,'signup.html', params)
        params = {'form': UserCreationForm, 'error': 'la clave no coicide'}
        return render(request,'signup.html', params)
#funcion para cerrar session
def cerrarSession(request):
    logout(request)
    return redirect('homeP')

#funcion para iniciar session
def initSession(request):
    params = {'form': AuthenticationForm}
    if request.method == 'GET':
        print('formulario')
        return render(request, 'signin.html', params)
    else:
        objtUser = authenticate(request, username=request.POST['username'],
                                password=request.POST['password'])
        if objtUser is None:
            params = params = {'form': AuthenticationForm,
                      'error':'usuario o clave incorrecta'}
            print('chek valoress')    
            return render(request, 'signin.html', params)
        else:
            login(request, objtUser)
            # Redirigir siempre al inicio
            return redirect('homeP')
        
#a ver que sigue
def dynamicmenu(request):
    try:
        ##
        menuList = MenuList.menuList_objects.values('menuname').order_by('Menutype').annotate(Count('menuname'))
        submenuList = MenuList.menuList_objects.filter(id__in = [1,2,3,4,5,6,7,8,9,10])
        mainmenu = menuserializer(menuList, many = True)
        data = mainmenu.data 
        print(data)
        request.session['mainM'] = data
        
        submenudata = submenuserializer(submenuList,many=True)
        subdata = submenudata.data 
        print(subdata)
        request.session['submenu'] = subdata
        return render(request, 'home.html', {})
    except Exception as identifier:
        return render(request, 'home.html', {})
    
@login_required
def loadPageMenu(request):
    """Vista para gestionar menús y módulos del sistema. Solo para administradores."""
    if not request.user.is_superuser:
        messages.error(request, "Acceso denegado.")
        return redirect('homeP')
    
    formaMenu = CrearMenu()
    formaSubMenu = CrearSubMenu()
    vModulos = ct_modulos.objects.filter(borrado=1)
    vSubModulos = ct_submodulos.objects.filter(borrado=1)
    params = {'formaMenu': formaMenu, 'formaSubMenu': formaSubMenu, 'modulos': vModulos, 'subModulos': vSubModulos }
    return render(request, 'pageMenu.html', params)

@login_required
#para crear menu
def crearMenu(request):
    """Crear un nuevo módulo/menú. Solo para administradores."""
    if not request.user.is_superuser:
        messages.error(request, "Acceso denegado.")
        return redirect('homeP')
    
    if request.method == 'POST':
        formaMenu = CrearMenu(request.POST)
        if formaMenu.is_valid():
            formaMenu.save()
            messages.success(request, "Módulo creado exitosamente.")
            return redirect('pageMenu')
        else:
            messages.error(request, "Error al crear el módulo. Verifica los datos.")
            params = {'formaMenu': formaMenu}
            return render(request, 'pageMenu.html', params)
    
    return redirect('pageMenu')

@login_required
def crearSubMenu(request):
    """Crear un nuevo submódulo/submenú. Solo para administradores."""
    if not request.user.is_superuser:
        messages.error(request, "Acceso denegado.")
        return redirect('homeP')
    
    if request.method == 'POST':
        formaSubMenu = CrearSubMenu(request.POST)
        if formaSubMenu.is_valid():
            formaSubMenu.save()
            messages.success(request, "Submódulo creado exitosamente.")
            return redirect('pageMenu')
        else:
            messages.error(request, "Error al crear el submódulo. Verifica los datos.")
            params = {'formaSubMenu': formaSubMenu}
            return render(request, 'pageMenu.html', params)
    
    return redirect('pageMenu')

@login_required
def eliminar_modulo(request, modulo_id):
    """Desactivar un módulo."""
    if not request.user.is_superuser:
        messages.error(request, "Acceso denegado.")
        return redirect('homeP')
    
    modulo = get_object_or_404(ct_modulos, id=modulo_id)
    
    try:
        modulo.borrado = False
        modulo.save()
        messages.success(request, f"Módulo '{modulo.nombre}' desactivado.")
    except Exception as e:
        messages.error(request, f"Error al desactivar el módulo: {str(e)}")
    
    return redirect('pageMenu')

@login_required
def activar_modulo(request, modulo_id):
    """Activar un módulo."""
    if not request.user.is_superuser:
        messages.error(request, "Acceso denegado.")
        return redirect('homeP')
    
    modulo = get_object_or_404(ct_modulos, id=modulo_id)
    
    try:
        modulo.borrado = True
        modulo.save()
        messages.success(request, f"Módulo '{modulo.nombre}' activado.")
    except Exception as e:
        messages.error(request, f"Error al activar el módulo: {str(e)}")
    
    return redirect('pageMenu')

@login_required
def eliminar_submodulo(request, submodulo_id):
    """Desactivar un submódulo."""
    if not request.user.is_superuser:
        messages.error(request, "Acceso denegado.")
        return redirect('homeP')
    
    submodulo = get_object_or_404(ct_submodulos, id=submodulo_id)
    
    try:
        submodulo.borrado = False
        submodulo.save()
        messages.success(request, f"Submódulo '{submodulo.nombre}' desactivado.")
    except Exception as e:
        messages.error(request, f"Error al desactivar el submódulo: {str(e)}")
    
    return redirect('pageMenu')

# primer contrato 
@login_required
def getMensajeContrat(request):
    #mensaje = contrato.obtener_mensaje()
    #params = {"getMsjSC": mensaje}
    return render(request, 'certificados.html')

#segundo contrato 123,esteban,trejo,barriga,236022004,mate,25/7/25
@login_required
def emitirCertificado(request):
    resultado = None
    params = {'resultado': resultado}

    if request.method == 'POST':
        id = int(request.POST['id'])
        nombre = request.POST['nombre']
        ap_paterno = request.POST['ap_paterno']
        ap_materno = request.POST['ap_materno']
        matricula = request.POST['matricula']
        curso = request.POST['curso']
        fecha = request.POST['fecha']

        try:
            receipt = contrato.emitir_certificado(id, nombre, ap_paterno, ap_materno, matricula, curso, fecha)
            resultado = f"Certificado emitido con éxito en el bloque {receipt['blocke']}, Hash emitido: {receipt['hash']}, Nonce emitido: {receipt['nonce']}, nonce: {receipt['nonce2']}"
            # receipt = blockchain_service.emitir_certificado(id, nombre, ap_paterno, ap_materno, matricula, curso, fecha)
            # if receipt.get('status') == 1:
            #     resultado = f"Certificado emitido con éxito. Hash de la transacción: {receipt['hash']}"
            #     messages.success(request, resultado)
            # else:
            #     resultado = "La transacción para emitir el certificado falló."
            #     messages.error(request, resultado)

            params = {'resultado': resultado}
        except Exception as e:
            resultado = f"Error: {str(e)}"
            resultado = f"Error al emitir certificado: {str(e)}"
            messages.error(request, resultado)
            params = {'resultado': resultado}

    return render(request, 'certificados.html', params)

#funcion para consultar contrato
@login_required
def consultarCertificado(request):
    datos = None
    error = None
    params = {'datos': datos, 'error': error}
    if request.method == 'POST':
        try:
            id = int(request.POST['id'])
            print(f"Consultando certificado ID: {id}")  # Debug
            resultado = contrato.obtener_certificado(id)
            print(f"Resultado obtenido: {resultado}")  # Debug
            certificado_id = int(request.POST['id'])
            resultado = contrato.obtener_certificado(certificado_id)
            
            datos = {
                'nombre': resultado[0],
                'apellidoPaterno': resultado[1],
                'apellidoMaterno': resultado[2],
                'matricula': resultado[3],
                'curso': resultado[4],
                'fechaEmision': resultado[5],
                'esValido': resultado[6]
            }
            params = {'datos': datos, 'error': error}
            messages.success(request, f"Certificado con ID {certificado_id} encontrado.")
        except Exception as e:
            print(f"Error al consultar certificado: {str(e)}")  # Debug
            if "Certificado no existe" in str(e):
                error = f"El certificado con ID {request.POST.get('id', 'N/A')} no existe en la blockchain"
            elif "contract function" in str(e):
                error = "Error de conexión con el contrato. Verifica que Ganache esté ejecutándose y el contrato esté desplegado correctamente"
                error = f"El certificado con ID {request.POST.get('id', 'N/A')} no existe en la blockchain."
            elif "ConnectionError" in str(e):
                error = "Error de conexión con la blockchain. Verifica que Ganache esté ejecutándose y la configuración sea correcta."
            else:
                error = f"Error al consultar certificado: {str(e)}"
                error = f"Ocurrió un error inesperado: {str(e)}"
            params = {'datos': datos, 'error': error}
            messages.error(request, error)

    return render(request, 'certificados.html', params)

# ==================== VISTAS PARA DOCUMENTOS PERSONALES ====================

@login_required
def listar_documentos(request):
    """Vista para listar documentos"""
    # Si es superusuario, puede ver todos los documentos
    if request.user.is_superuser:
        documentos = DocumentoPersonal.objects.filter(
            borrado=1
        ).select_related('usuario', 'categoria').order_by('-fecha_subida')
    else:
        # Usuarios normales solo ven sus propios documentos
        documentos = DocumentoPersonal.objects.filter(
            usuario=request.user,
            borrado=1
        ).select_related('categoria').order_by('-fecha_subida')

    categorias = CategoriaDocumento.objects.filter(borrado=1)

    context = {
        'documentos': documentos,
        'categorias': categorias,
        'es_admin': request.user.is_superuser,  # Para mostrar opciones de admin en el template
    }
    return render(request, 'documentos/listar_documentos.html', context)

@login_required
def subir_documento(request):
    """Vista unificada para subir un nuevo documento (personal, de admisión, académico o de titulación)."""
    is_student = hasattr(request.user, 'alumno')
    alumno_logueado = request.user.alumno if is_student else None
    

    if request.method == 'POST':
        try:
            tipo_documento_form = request.POST.get('tipo_documento')

            # 1. Determinar el usuario y alumno objetivo de forma robusta
            alumno_objetivo = None
            usuario_objetivo = None

            if request.user.is_superuser:
                # Si es admin, DEBE seleccionar un alumno del formulario.
                alumno_id = request.POST.get('alumno')
                if not alumno_id:
                    messages.error(request, "Como administrador, debe seleccionar un alumno para asignarle el documento.")
                    raise ValueError("Alumno no especificado por el administrador.")
                
                alumno_objetivo = get_object_or_404(Alumno, id=alumno_id)
                usuario_objetivo = alumno_objetivo.usuario
            else:
                # Si no es admin, el objetivo es el propio usuario logueado.
                usuario_objetivo = request.user
                if is_student:
                    if alumno_logueado:
                        alumno_objetivo = alumno_logueado
                    else:
                        # Si el usuario debería ser alumno pero no se encuentra el perfil
                        try:
                            alumno_objetivo = Alumno.objects.get(usuario=request.user, borrado=1)
                        except Alumno.DoesNotExist:
                            alumno_objetivo = None

            # 2. Crear el documento según el tipo
            if tipo_documento_form == 'personal':
                # Para documentos personales, usar la primera categoría personal disponible
                categoria = CategoriaDocumento.objects.filter(tipo='personal', borrado=1).first()
                if not categoria:
                    messages.error(request, 'No hay categorías de documentos personales disponibles.')
                    return redirect('subir_documento')
                
                DocumentoPersonal.objects.create(
                    usuario=usuario_objetivo,
                    categoria=categoria,
                    nombre_documento=request.POST.get('nombre_documento'),
                    descripcion=request.POST.get('descripcion', ''),
                    archivo=request.FILES.get('archivo'),
                )
                messages.success(request, f'Documento personal subido para {usuario_objetivo.username}.')

            elif tipo_documento_form in ['academico', 'titulacion']:
                if not alumno_objetivo:
                    messages.error(request, "Se requiere un perfil de alumno para subir documentos académicos o de titulación. Contacte al administrador para crear su perfil de alumno.")
                    return redirect('subir_documento')

                # Determinar el tipo de documento académico basado en el tipo seleccionado
                if tipo_documento_form == 'titulacion':
                    tipo_academico = 'titulo'  # Por defecto para titulación
                else:
                    tipo_academico = 'certificado'  # Por defecto para académico

                DocumentoAcademico.objects.create(
                    alumno=alumno_objetivo,
                    tipo_documento=tipo_academico,
                    titulo=request.POST.get('nombre_documento'),
                    descripcion=request.POST.get('descripcion', ''),
                    archivo=request.FILES.get('archivo'),
                    periodo_academico=request.POST.get('periodo_academico', ''),
                )
                msg = 'académico' if tipo_documento_form == 'academico' else 'de titulación'
                messages.success(request, f'Documento {msg} subido para {alumno_objetivo.nombre_completo}.')
            
            # 3. Redirigir
            if alumno_objetivo:
                return redirect('detalle_alumno', alumno_id=alumno_objetivo.id)
            else:
                # Aspirante (sin perfil de alumno) subiendo su propio documento
                return redirect('listar_documentos')

        except Exception as e:
            messages.error(request, f'Error al subir documento: {str(e)}')

    return render(request, 'documentos/subir_documento.html', {})

@login_required
def editar_documento(request, documento_id):
    """Vista para editar un documento existente"""
    # Si es superusuario, puede editar cualquier documento
    if request.user.is_superuser:
        documento = get_object_or_404(DocumentoPersonal, id=documento_id, borrado=1)
    else:
        # Usuarios normales solo pueden editar sus propios documentos
        documento = get_object_or_404(DocumentoPersonal, id=documento_id, usuario=request.user, borrado=1)

    if request.method == 'POST':
        try:
            estado_anterior = documento.estado  # Guardar estado anterior

            categoria_id = request.POST.get('categoria')
            categoria = get_object_or_404(CategoriaDocumento, id=categoria_id)

            documento.categoria = categoria
            documento.nombre_documento = request.POST.get('nombre_documento')
            documento.descripcion = request.POST.get('descripcion', '')
            documento.fecha_vencimiento = request.POST.get('fecha_vencimiento') or None

            # Si se sube un nuevo archivo o si el documento fue rechazado, se vuelve a poner en pendiente para revisión.
            if request.FILES.get('archivo') or estado_anterior == 'rechazado':
                documento.estado = 'pendiente'
                documento.observaciones = ''  # Limpiar observaciones al reenviar para revisión

            if request.FILES.get('archivo'):
                documento.archivo = request.FILES.get('archivo')

            documento.save()

            if (request.FILES.get('archivo') or estado_anterior == 'rechazado') and not request.user.is_superuser:
                messages.success(request, 'Documento actualizado. Será revisado nuevamente por un administrador.')
            else:
                messages.success(request, 'Documento actualizado exitosamente.')

            # Redirigir según el tipo de usuario
            if hasattr(request.user, 'alumno'):
                return redirect('detalle_alumno', alumno_id=request.user.alumno.id)
            else:
                return redirect('listar_documentos')

        except Exception as e:
            messages.error(request, f'Error al actualizar documento: {str(e)}')

    categorias = CategoriaDocumento.objects.filter(borrado=1)
    context = {
        'documento': documento,
        'categorias': categorias,
    }
    return render(request, 'documentos/editar_documento.html', context)

@login_required
@login_required
def eliminar_documento(request, documento_id):
    """Vista para eliminar (marcar como borrado) un documento"""
    # Solo superusuarios pueden eliminar documentos desde el cardex
    if not request.user.is_superuser:
        messages.error(request, 'No tienes permisos para eliminar documentos.')
        return redirect('listar_documentos')
    
    documento = get_object_or_404(DocumentoPersonal, id=documento_id, borrado=1)

    if request.method == 'POST':
        documento.borrado = 0
        documento.save()
        messages.success(request, 'Documento eliminado exitosamente.')
        return redirect('gestionar_documentos_personales')

    return redirect('listar_documentos')

@login_required
def gestionar_documentos_personales(request):
    """Vista para listar documentos personales del sistema (admin) o del usuario (alumno)"""
    is_admin = request.user.is_superuser
    
    if is_admin:
        # Admin ve todos los documentos personales
        documentos = DocumentoPersonal.objects.filter(
            borrado=1
        ).select_related('usuario', 'categoria', 'usuario__alumno').order_by('-fecha_subida')
    else:
        # Usuario normal ve solo sus documentos personales
        if hasattr(request.user, 'alumno'):
            documentos = DocumentoPersonal.objects.filter(
                usuario=request.user,
                borrado=1
            ).select_related('categoria').order_by('-fecha_subida')
        else:
            documentos = DocumentoPersonal.objects.none()
    
    # Filtros
    estado = request.GET.get('estado', '')
    alumno_id = request.GET.get('alumno', '')
    
    if estado:
        documentos = documentos.filter(estado=estado)
    
    if alumno_id and is_admin:
        documentos = documentos.filter(usuario__alumno__id=alumno_id)
    
    # Obtener lista de alumnos para el filtro (solo para admin)
    alumnos = []
    if is_admin:
        alumnos = Alumno.objects.filter(borrado=1).select_related('usuario').order_by('nombre', 'apellido_paterno', 'apellido_materno')

    context = {
        'documentos': documentos,
        'es_admin': is_admin,
        'estado_seleccionado': estado,
        'alumno_seleccionado': alumno_id,
        'alumnos': alumnos,
    }
    return render(request, 'documentos/listar_documentos_personales.html', context)


@login_required
def revisar_documento_personal(request, documento_id):
    """Vista para que un administrador revise (apruebe/rechace) un documento personal."""
    if not request.user.is_superuser:
        messages.error(request, "Acceso denegado.")
        return redirect('listar_documentos')

    documento = get_object_or_404(DocumentoPersonal, id=documento_id, borrado=1)

    if request.method == 'POST':
        try:
            accion = request.POST.get('accion')
            observaciones = request.POST.get('observaciones', '')

            if accion == 'aprobar':
                documento.estado = 'aprobado'
                documento.observaciones = ''  # Limpiar observaciones si se aprueba
                messages.success(request, 'Documento aprobado exitosamente.')
            elif accion == 'rechazar':
                documento.estado = 'rechazado'
                documento.observaciones = observaciones
                messages.error(request, 'Documento rechazado.')

            documento.save()
            return redirect('gestionar_documentos_personales')

        except Exception as e:
            messages.error(request, f'Error al procesar el documento: {str(e)}')

    context = {
        'documento': documento,
    }
    return render(request, 'documentos/revisar_documento_personal.html', context)

# ==================== VISTA PARA CARDEX UNIFICADO DE DOCUMENTOS ====================

@login_required
def gestionar_documentos_unificado(request):
    """
    Vista unificada para que los administradores gestionen TODOS los documentos 
    (personales y académicos) en un solo lugar.
    """
    if not request.user.is_superuser:
        messages.error(request, "Acceso denegado. Solo los administradores pueden acceder a esta página.")
        return redirect('homeP')

    # Obtener filtros de la URL
    tipo_filtro = request.GET.get('tipo', '')
    estado_filtro = request.GET.get('estado', '')
    usuario_filtro = request.GET.get('usuario', '')

    # 1. Obtener documentos personales
    docs_personales = DocumentoPersonal.objects.filter(borrado=1).select_related('usuario', 'categoria')
    
    # 2. Obtener documentos académicos
    docs_academicos = DocumentoAcademico.objects.filter(borrado=1).select_related('alumno__usuario')

    # Aplicar filtros
    if usuario_filtro:
        docs_personales = docs_personales.filter(usuario_id=usuario_filtro)
        docs_academicos = docs_academicos.filter(alumno__usuario_id=usuario_filtro)

    if estado_filtro:
        docs_personales = docs_personales.filter(estado=estado_filtro)
        docs_academicos = docs_academicos.filter(estado_revision=estado_filtro)
    
    # 3. Unificar los documentos en una sola lista con una estructura común
    documentos_unificados = []
    tipos_titulacion = ['titulo', 'cedula', 'acta_examen', 'liberacion_ss']

    for doc in docs_personales:
        tipo_general = 'Personal'
        if doc.categoria.tipo == 'admision':
            tipo_general = 'Aspirante'

        documentos_unificados.append({
            'id': doc.id,
            'tipo_general': tipo_general,
            'titulo': doc.nombre_documento,
            'tipo_especifico': doc.categoria.nombre,
            'usuario': doc.usuario,
            'fecha_subida': doc.fecha_subida,
            'estado': doc.estado,
            'url_revision': reverse('revisar_documento_personal', args=[doc.id]),
            'archivo_url': doc.archivo.url if doc.archivo else None,
        })

    for doc in docs_academicos:
        tipo_general = 'Titulación' if doc.tipo_documento in tipos_titulacion else 'Académico'

        documentos_unificados.append({
            'id': doc.id,
            'tipo_general': tipo_general,
            'titulo': doc.titulo,
            'tipo_especifico': doc.get_tipo_documento_display(),
            'usuario': doc.alumno.usuario,
            'fecha_subida': doc.fecha_subida,
            'estado': doc.estado_revision,
            'url_revision': reverse('revisar_documento_academico', args=[doc.id]),
            'archivo_url': doc.archivo.url if doc.archivo else None,
        })

    # 4. Ordenar la lista combinada por fecha de subida (más recientes primero)
    documentos_unificados.sort(key=lambda x: x['fecha_subida'], reverse=True)

    # Aplicar filtro de tipo general ('Personal' o 'Académico')
    if tipo_filtro:
        documentos_unificados = [doc for doc in documentos_unificados if doc['tipo_general'] == tipo_filtro]

    # 5. Preparar contexto para la plantilla
    usuarios = User.objects.filter(is_active=True).order_by('username')
    
    context = {
        'documentos': documentos_unificados,
        'usuarios': usuarios,
        'tipo_seleccionado': tipo_filtro,
        'estado_seleccionado': estado_filtro,
        'usuario_seleccionado': int(usuario_filtro) if usuario_filtro else None,
    }

    return render(request, 'admin/gestionar_documentos_unificado.html', context)

# ==================== VISTAS PARA CARDEX ACADÉMICO ====================

@login_required
def dashboard_cardex(request):
    """Dashboard principal del cardex académico"""
    # Estadísticas generales
    total_alumnos = Alumno.objects.filter(borrado=1).count()
    total_carreras = Carrera.objects.filter(borrado=1).count()

    # Créditos pendientes (materias no aprobadas)
    creditos_pendientes = Calificacion.objects.filter(
        borrado=1,
        estado__in=['cursando', 'reprobada']
    ).aggregate(total_creditos=Sum('materia__creditos'))['total_creditos'] or 0

    # Documentos subidos hoy
    hoy = timezone.now().date()
    documentos_hoy = DocumentoAcademico.objects.filter(
        borrado=1,
        fecha_subida__date=hoy
    ).count()

    # Alumnos con bajo promedio (< 7.0)
    alumnos_bajo_promedio = []
    alumnos = Alumno.objects.filter(borrado=1).select_related('carrera')
    for alumno in alumnos:
        promedio = alumno.promedio_general
        if promedio > 0 and promedio < 7.0:
            alumnos_bajo_promedio.append(alumno)

    # Documentos recientes
    documentos_recientes = DocumentoAcademico.objects.filter(
        borrado=1
    ).select_related('alumno').order_by('-fecha_subida')[:10]

    context = {
        'total_alumnos': total_alumnos,
        'total_carreras': total_carreras,
        'creditos_pendientes': creditos_pendientes,
        'documentos_hoy': documentos_hoy,
        'alumnos_bajo_promedio': alumnos_bajo_promedio[:5],  # Mostrar solo los primeros 5
        'documentos_recientes': documentos_recientes,
    }
    return render(request, 'cardex/dashboard.html', context)

@login_required
def listar_alumnos(request):
    """Vista para listar alumnos"""
    # Los alumnos no deben poder acceder a esta lista
    if hasattr(request.user, 'alumno'):
        messages.error(request, "Acceso denegado.")
        return redirect('detalle_alumno', alumno_id=request.user.alumno.id)

    alumnos = Alumno.objects.filter(borrado=1).select_related('carrera').order_by('apellido_paterno')

    # Filtros opcionales
    carrera_id = request.GET.get('carrera')
    estado = request.GET.get('estado')
    semestre = request.GET.get('semestre')

    if carrera_id:
        alumnos = alumnos.filter(carrera_id=carrera_id)
    if estado:
        alumnos = alumnos.filter(estado=estado)
    if semestre:
        alumnos = alumnos.filter(semestre_actual=semestre)

    carreras = Carrera.objects.filter(borrado=1)
    semestres = range(1, 13)  # Semestres del 1 al 12

    context = {
        'alumnos': alumnos,
        'carreras': carreras,
        'carrera_seleccionada': carrera_id,
        'estado_seleccionado': estado,
        'semestre_seleccionado': semestre,
        'semestres': semestres,
    }
    return render(request, 'cardex/listar_alumnos.html', context)

@login_required
def crear_alumno(request):
    """Vista para crear un nuevo alumno"""
    if request.method == 'POST':
        try:
            carrera_id = request.POST.get('carrera')
            carrera = get_object_or_404(Carrera, id=carrera_id)

            # Obtener institución de procedencia si se seleccionó
            institucion_id = request.POST.get('institucion_procedencia')
            institucion = None
            if institucion_id:
                institucion = get_object_or_404(InstitucionProcedencia, id=institucion_id)

            # Crear usuario primero
            username = request.POST.get('matricula')
            user = User.objects.create_user(
                username=username,
                email=request.POST.get('email'),
                password=request.POST.get('password'),
                first_name=request.POST.get('nombre'),
                last_name=f"{request.POST.get('apellido_paterno')} {request.POST.get('apellido_materno')}"
            )

            alumno = Alumno(
                usuario=user,
                matricula=request.POST.get('matricula'),
                nombre=request.POST.get('nombre'),
                apellido_paterno=request.POST.get('apellido_paterno'),
                apellido_materno=request.POST.get('apellido_materno'),
                fecha_nacimiento=request.POST.get('fecha_nacimiento'),
                carrera=carrera,
                institucion_procedencia=institucion,
                semestre_actual=request.POST.get('semestre_actual', 1),
                telefono=request.POST.get('telefono'),
                email_institucional=request.POST.get('email_institucional'),
                curp=request.POST.get('curp')
            )
            alumno.save()

            messages.success(request, 'Alumno creado exitosamente.')
            return redirect('listar_alumnos')

        except Exception as e:
            messages.error(request, f'Error al crear alumno: {str(e)}')

    carreras = Carrera.objects.filter(borrado=1)
    instituciones = InstitucionProcedencia.objects.filter(borrado=1)
    return render(request, 'cardex/crear_alumno.html', {
        'carreras': carreras,
        'instituciones': instituciones
    })

@login_required
def detalle_alumno(request, alumno_id):
    """Vista para ver el detalle completo de un alumno"""
    # Si el usuario es un alumno, solo puede ver su propio perfil

    is_student = hasattr(request.user, 'alumno')
    # Permitir acceso a superusuarios y a Jefatura de División
    es_jefatura_division = False
    if hasattr(request.user, 'perfil_usuario') and request.user.perfil_usuario.perfil_fk:
        es_jefatura_division = request.user.perfil_usuario.perfil_fk.nombre.strip().lower() in [
            'jefatura de división', 'jefatura de division', 'jefatura division', 'jefatura'
        ]

    if is_student and request.user.alumno.id != alumno_id and not request.user.is_superuser and not es_jefatura_division:
        messages.error(request, "No tienes permiso para ver los detalles de otro alumno.")
        return redirect('detalle_alumno', alumno_id=request.user.alumno.id)

    alumno = get_object_or_404(Alumno, id=alumno_id, borrado=1)

    # Calificaciones del alumno
    calificaciones = Calificacion.objects.filter(
        alumno=alumno,
        borrado=1
    ).select_related('materia').order_by('-fecha_registro')

    # Documentos académicos
    documentos_academicos = DocumentoAcademico.objects.filter(
        alumno=alumno,
        borrado=1
    ).order_by('-fecha_subida')

    # Documentos personales
    documentos_personales_query = DocumentoPersonal.objects.filter(
        usuario=alumno.usuario,
        borrado=1
    ).select_related('categoria').order_by('-fecha_subida')

    # Solo documentos personales (sin aspirantes)
    documentos_personales = [doc for doc in documentos_personales_query if doc.categoria.tipo == 'personal']

    # Separar documentos de titulación de los demás documentos académicos
    tipos_titulacion = ['titulo', 'cedula', 'acta_examen', 'liberacion_ss']
    documentos_titulacion = [doc for doc in documentos_academicos if doc.tipo_documento in tipos_titulacion]
    otros_documentos_academicos = [doc for doc in documentos_academicos if doc.tipo_documento not in tipos_titulacion]

    # Estadísticas
    promedio_general = alumno.promedio_general
    total_materias_aprobadas = calificaciones.filter(estado__in=['aprobada', 'aprobado']).count()
    total_materias_cursando = calificaciones.filter(estado='cursando').count()

    # Calcular total de créditos aprobados
    calificaciones_aprobadas = calificaciones.filter(estado__in=['aprobada', 'aprobado'])
    total_creditos_aprobados = calificaciones_aprobadas.aggregate(
        total_creditos=Sum('materia__creditos')
    )['total_creditos'] or 0

    # Calcular total de créditos cursando
    calificaciones_cursando = calificaciones.filter(estado='cursando')
    total_creditos_cursando = calificaciones_cursando.aggregate(
        total_creditos=Sum('materia__creditos')
    )['total_creditos'] or 0

    # Total de créditos acumulados (aprobados + cursando)
    total_creditos_acumulados = total_creditos_aprobados + total_creditos_cursando

    # Calcular créditos pendientes (materias no aprobadas del alumno)
    calificaciones_pendientes = calificaciones.filter(estado__in=['cursando', 'reprobada'])
    total_creditos_pendientes = calificaciones_pendientes.aggregate(
        total_creditos=Sum('materia__creditos')
    )['total_creditos'] or 0

    context = {
        'alumno': alumno,
        'calificaciones': calificaciones,
        'documentos': otros_documentos_academicos, # Ahora solo contiene los no relacionados a titulación
        'documentos_titulacion': documentos_titulacion,
        'documentos_personales': documentos_personales,
        'promedio_general': promedio_general,
        'total_materias_aprobadas': total_materias_aprobadas,
        'total_materias_cursando': total_materias_cursando,
        'total_creditos_aprobados': total_creditos_aprobados,
        'total_creditos_cursando': total_creditos_cursando,
        'total_creditos_acumulados': total_creditos_acumulados,
        'total_creditos_pendientes': total_creditos_pendientes,
    }
    return render(request, 'cardex/detalle_alumno.html', context)

@login_required
def generar_hash_alumno(request, alumno_id):
    """Vista para generar hash de blockchain con toda la información del alumno"""
    # Solo administradores pueden generar hashes
    if not request.user.is_superuser:
        messages.error(request, 'No tienes permisos para generar hashes de blockchain.')
        return redirect('detalle_alumno', alumno_id=alumno_id)
    
    alumno = get_object_or_404(Alumno, id=alumno_id, borrado=1)
    
    # Verificar que el alumno tenga CURP (requerido para el hash)
    if not alumno.curp:
        messages.error(request, 'El alumno debe tener CURP para generar el hash de blockchain.')
        return redirect('detalle_alumno', alumno_id=alumno_id)
    
    try:
        # Recopilar toda la información del alumno
        informacion_completa = {
            'id': alumno.id,
            'matricula': alumno.matricula,
            'nombre_completo': alumno.nombre_completo,
            'curp': alumno.curp,
            'fecha_nacimiento': str(alumno.fecha_nacimiento),
            'carrera': alumno.carrera.nombre,
            'semestre_actual': alumno.semestre_actual,
            'estado': alumno.estado,
            'fecha_ingreso': str(alumno.fecha_ingreso),
            'telefono': alumno.telefono or '',
            'email_institucional': alumno.email_institucional or '',
            'institucion_procedencia': alumno.institucion_procedencia.nombre if alumno.institucion_procedencia else '',
        }
        
        # Obtener calificaciones
        calificaciones = Calificacion.objects.filter(alumno=alumno, borrado=1)
        calificaciones_data = []
        for cal in calificaciones:
            calificaciones_data.append({
                'materia': cal.materia.nombre,
                'calificacion': str(cal.calificacion) if cal.calificacion else 'Sin calificar',
                'estado': cal.estado,
                'periodo': cal.periodo,
                'fecha_registro': str(cal.fecha_registro)
            })
        
        # Obtener documentos académicos
        documentos_academicos = DocumentoAcademico.objects.filter(alumno=alumno, borrado=1)
        docs_academicos_data = []
        for doc in documentos_academicos:
            docs_academicos_data.append({
                'tipo': doc.tipo_documento,
                'titulo': doc.titulo,
                'fecha_subida': str(doc.fecha_subida),
                'estado': doc.estado_revision
            })
        
        # Obtener documentos personales
        documentos_personales = DocumentoPersonal.objects.filter(
            usuario=alumno.usuario, 
            borrado=1,
            categoria__tipo='personal'
        )
        docs_personales_data = []
        for doc in documentos_personales:
            docs_personales_data.append({
                'categoria': doc.categoria.nombre,
                'nombre_documento': doc.nombre_documento,
                'fecha_subida': str(doc.fecha_subida),
                'estado': doc.estado
            })
        
        # Crear un hash único con toda la información
        datos_completos = {
            'informacion_personal': informacion_completa,
            'calificaciones': calificaciones_data,
            'documentos_academicos': docs_academicos_data,
            'documentos_personales': docs_personales_data,
            'timestamp': datetime.now().isoformat()
        }
        
        # Convertir a string para hashing
        datos_string = json.dumps(datos_completos, sort_keys=True, ensure_ascii=False)
        hash_completo = hashlib.sha256(datos_string.encode('utf-8')).hexdigest()
        
        # Generar hash en blockchain usando la función existente
        receipt = contrato.emitir_hash_alumno(
            alumno_id=alumno.id,
            curp=alumno.curp,
            matricula=alumno.matricula,
            nombre_completo=alumno.nombre_completo,
            carrera=alumno.carrera.nombre,
            fecha_nacimiento=str(alumno.fecha_nacimiento)
        )
        
        # Actualizar el alumno con la información del hash
        alumno.hash_alumno = hash_completo
        alumno.fecha_emision_hash = timezone.now()
        alumno.save()
        
        # Preparar contexto para mostrar la información
        context = {
            'alumno': alumno,
            'hash_completo': hash_completo,
            'receipt': receipt,
            'informacion_completa': informacion_completa,
            'calificaciones_count': len(calificaciones_data),
            'documentos_academicos_count': len(docs_academicos_data),
            'documentos_personales_count': len(docs_personales_data),
        }
        
        messages.success(request, f'Hash de blockchain generado exitosamente para {alumno.nombre_completo}.')
        return render(request, 'cardex/hash_alumno.html', context)
        
    except Exception as e:
        messages.error(request, f'Error al generar hash de blockchain: {str(e)}')
        return redirect('detalle_alumno', alumno_id=alumno_id)

@login_required
def generar_certificado_documento(request, documento_id, tipo_documento):
    """Vista para generar certificado de blockchain para un documento específico"""
    # Solo administradores pueden generar certificados
    if not request.user.is_superuser:
        messages.error(request, 'No tienes permisos para generar certificados de blockchain.')
        return redirect('detalle_alumno', alumno_id=1)  # Redirigir a una página válida
    
    try:
        # Obtener el documento según el tipo
        if tipo_documento == 'academico':
            documento = get_object_or_404(DocumentoAcademico, id=documento_id, borrado=1)
            alumno = documento.alumno
        elif tipo_documento == 'personal':
            documento = get_object_or_404(DocumentoPersonal, id=documento_id, borrado=1)
            alumno = get_object_or_404(Alumno, usuario=documento.usuario, borrado=1)
        else:
            messages.error(request, 'Tipo de documento no válido.')
            return redirect('detalle_alumno', alumno_id=1)
        
        # Verificar que el alumno tenga CURP
        if not alumno.curp:
            messages.error(request, 'El alumno debe tener CURP para generar certificados de blockchain.')
            return redirect('detalle_alumno', alumno_id=alumno.id)
        
        # Verificar que el documento esté aprobado
        if tipo_documento == 'academico' and documento.estado_revision != 'aprobado':
            messages.error(request, 'Solo se pueden certificar documentos que hayan sido aprobados.')
            return redirect('detalle_alumno', alumno_id=alumno.id)
        elif tipo_documento == 'personal' and documento.estado != 'aprobado':
            messages.error(request, 'Solo se pueden certificar documentos que hayan sido aprobados.')
            return redirect('detalle_alumno', alumno_id=alumno.id)
        
        # Verificar si el documento ya está certificado
        if tipo_documento == 'academico' and documento.certificado_hash:
            messages.info(request, 'Este documento ya está certificado. Redirigiendo a la vista del certificado.')
            return redirect('ver_certificado_documento', documento_id=documento_id, tipo_documento=tipo_documento)
        elif tipo_documento == 'personal' and documento.certificado_hash:
            messages.info(request, 'Este documento ya está certificado. Redirigiendo a la vista del certificado.')
            return redirect('ver_certificado_documento', documento_id=documento_id, tipo_documento=tipo_documento)
        
        # Crear información completa del documento para el hash
        informacion_documento = {
            'tipo_documento': tipo_documento,
            'documento_id': documento.id,
            'alumno_id': alumno.id,
            'alumno_matricula': alumno.matricula,
            'alumno_nombre_completo': alumno.nombre_completo,
            'alumno_curp': alumno.curp,
            'fecha_generacion': datetime.now().isoformat(),
        }
        
        # Agregar información específica según el tipo de documento
        if tipo_documento == 'academico':
            informacion_documento.update({
                'titulo': documento.titulo,
                'tipo_documento_academico': documento.tipo_documento,
                'descripcion': documento.descripcion or '',
                'periodo_academico': documento.periodo_academico or '',
                'estado_revision': documento.estado_revision,
                'fecha_subida': str(documento.fecha_subida),
            })
        elif tipo_documento == 'personal':
            informacion_documento.update({
                'nombre_documento': documento.nombre_documento,
                'categoria': documento.categoria.nombre,
                'descripcion': documento.descripcion or '',
                'estado': documento.estado,
                'fecha_subida': str(documento.fecha_subida),
                'fecha_vencimiento': str(documento.fecha_vencimiento) if documento.fecha_vencimiento else '',
            })
        
        # Crear hash único del documento
        datos_string = json.dumps(informacion_documento, sort_keys=True, ensure_ascii=False)
        hash_documento = hashlib.sha256(datos_string.encode('utf-8')).hexdigest()
        
        # Generar certificado en blockchain
        # Crear ID descriptivo con CURP y tipo de documento abreviado
        abreviacion = obtener_abreviacion_tipo_documento(tipo_documento, documento)
        timestamp = int(datetime.now().timestamp())
        certificado_id = f"{alumno.curp}_{abreviacion}_{documento_id}_{timestamp}"
        
        # Preparar datos para el contrato blockchain
        nombre_completo = alumno.nombre_completo
        curp = alumno.curp
        matricula = alumno.matricula
        carrera = alumno.carrera.nombre
        
        # Título del certificado basado en el tipo de documento
        if tipo_documento == 'academico':
            titulo_certificado = f"Certificado {documento.tipo_documento}: {documento.titulo}"
        else:
            titulo_certificado = f"Certificado {documento.categoria.nombre}: {documento.nombre_documento}"
        
        # Emitir certificado en blockchain
        receipt = contrato.emitir_certificado(
            id=int(certificado_id.split('_')[-1]),  # Usar timestamp como ID numérico
            nombre=nombre_completo,
            ap_paterno=curp,  # Usar CURP como apellido paterno
            ap_materno=matricula,  # Usar matrícula como apellido materno
            matricula=carrera,  # Usar carrera como matrícula
            curso=titulo_certificado,
            fecha=datetime.now().strftime("%d/%m/%Y")
        )
        
        # Actualizar el documento con la información del certificado
        if tipo_documento == 'academico':
            documento.certificado_id = certificado_id
            documento.certificado_hash = receipt.get('hash')  # Hash de la transacción blockchain
            documento.fecha_emision_certificado = timezone.now()
            documento.save()
        elif tipo_documento == 'personal':
            documento.certificado_id = certificado_id
            documento.certificado_hash = receipt.get('hash')  # Hash de la transacción blockchain
            documento.fecha_emision_certificado = timezone.now()
            documento.save()
        
        # Preparar contexto para mostrar la información
        context = {
            'documento': documento,
            'alumno': alumno,
            'tipo_documento': tipo_documento,
            'hash_documento': receipt.get('hash'),  # Hash de la transacción blockchain
            'certificado_id': certificado_id,
            'receipt': receipt,
            'informacion_documento': informacion_documento,
            'titulo_certificado': titulo_certificado,
        }
        
        messages.success(request, f'Certificado de blockchain generado exitosamente para el documento.')
        return render(request, 'documentos/certificado_documento.html', context)
        
    except Exception as e:
        messages.error(request, f'Error al generar certificado de blockchain: {str(e)}')
        return redirect('detalle_alumno', alumno_id=1)

@login_required
def ver_certificado_documento(request, documento_id, tipo_documento):
    """Vista para ver un certificado existente de un documento"""
    # Solo administradores pueden ver certificados
    if not request.user.is_superuser:
        messages.error(request, 'No tienes permisos para ver certificados de blockchain.')
        return redirect('detalle_alumno', alumno_id=1)
    
    try:
        # Obtener el documento según el tipo
        if tipo_documento == 'academico':
            documento = get_object_or_404(DocumentoAcademico, id=documento_id, borrado=1)
            alumno = documento.alumno
        elif tipo_documento == 'personal':
            documento = get_object_or_404(DocumentoPersonal, id=documento_id, borrado=1)
            alumno = get_object_or_404(Alumno, usuario=documento.usuario, borrado=1)
        else:
            messages.error(request, 'Tipo de documento no válido.')
            return redirect('detalle_alumno', alumno_id=1)
        
        # Verificar que el documento esté certificado
        if not documento.certificado_hash or not documento.certificado_id:
            messages.error(request, 'Este documento no está certificado.')
            return redirect('detalle_alumno', alumno_id=alumno.id)
        
        # Recrear la información del certificado
        informacion_documento = {
            'tipo_documento': tipo_documento,
            'documento_id': documento.id,
            'alumno_id': alumno.id,
            'alumno_matricula': alumno.matricula,
            'alumno_nombre_completo': alumno.nombre_completo,
            'alumno_curp': alumno.curp,
            'fecha_generacion': documento.fecha_emision_certificado.isoformat() if documento.fecha_emision_certificado else datetime.now().isoformat(),
        }
        
        # Agregar información específica según el tipo de documento
        if tipo_documento == 'academico':
            informacion_documento.update({
                'titulo': documento.titulo,
                'tipo_documento_academico': documento.tipo_documento,
                'descripcion': documento.descripcion or '',
                'periodo_academico': documento.periodo_academico or '',
                'estado_revision': documento.estado_revision,
                'fecha_subida': str(documento.fecha_subida),
            })
        elif tipo_documento == 'personal':
            informacion_documento.update({
                'nombre_documento': documento.nombre_documento,
                'categoria': documento.categoria.nombre,
                'descripcion': documento.descripcion or '',
                'estado': documento.estado,
                'fecha_subida': str(documento.fecha_subida),
                'fecha_vencimiento': str(documento.fecha_vencimiento) if documento.fecha_vencimiento else '',
            })
        
        # Título del certificado basado en el tipo de documento
        if tipo_documento == 'academico':
            titulo_certificado = f"Certificado {documento.tipo_documento}: {documento.titulo}"
        else:
            titulo_certificado = f"Certificado {documento.categoria.nombre}: {documento.nombre_documento}"
        
        # Preparar contexto para mostrar la información
        context = {
            'documento': documento,
            'alumno': alumno,
            'tipo_documento': tipo_documento,
            'hash_documento': documento.certificado_hash or 'No disponible',
            'certificado_id': documento.certificado_id or 'No disponible',
            'receipt': None,  # No tenemos el receipt original
            'informacion_documento': informacion_documento,
            'titulo_certificado': titulo_certificado,
            'es_certificado_existente': True,
        }
        
        return render(request, 'documentos/certificado_documento.html', context)
        
    except Exception as e:
        messages.error(request, f'Error al ver certificado: {str(e)}')
        return redirect('detalle_alumno', alumno_id=1)

@login_required
def editar_alumno(request, alumno_id):
    """Vista para editar un alumno (solo administradores)"""
    if not request.user.is_superuser:
        messages.error(request, 'No tienes permisos para editar alumnos.')
        return redirect('listar_alumnos')

    alumno = get_object_or_404(Alumno, id=alumno_id, borrado=1)

    if request.method == 'POST':
        try:
            # Actualizar datos del usuario
            user = alumno.usuario
            user.first_name = request.POST.get('nombre')
            user.last_name = f"{request.POST.get('apellido_paterno')} {request.POST.get('apellido_materno')}"
            user.email = request.POST.get('email')
            user.save()

            # Actualizar datos del alumno
            carrera_id = request.POST.get('carrera')
            carrera = get_object_or_404(Carrera, id=carrera_id)

            # Obtener institución de procedencia si se seleccionó
            institucion_id = request.POST.get('institucion_procedencia')
            institucion = None
            if institucion_id:
                institucion = get_object_or_404(InstitucionProcedencia, id=institucion_id)

            alumno.matricula = request.POST.get('matricula')
            alumno.nombre = request.POST.get('nombre')
            alumno.apellido_paterno = request.POST.get('apellido_paterno')
            alumno.apellido_materno = request.POST.get('apellido_materno')
            alumno.fecha_nacimiento = request.POST.get('fecha_nacimiento')
            alumno.carrera = carrera
            alumno.institucion_procedencia = institucion
            alumno.semestre_actual = request.POST.get('semestre_actual')
            alumno.estado = request.POST.get('estado')
            alumno.telefono = request.POST.get('telefono')
            alumno.email_institucional = request.POST.get('email_institucional')
            alumno.curp = request.POST.get('curp')
            alumno.save()

            messages.success(request, 'Alumno actualizado exitosamente.')
            return redirect('detalle_alumno', alumno_id=alumno_id)

        except Exception as e:
            messages.error(request, f'Error al actualizar alumno: {str(e)}')

    # Datos para los formularios
    carreras = Carrera.objects.filter(borrado=1)
    instituciones = InstitucionProcedencia.objects.filter(borrado=1)

    context = {
        'alumno': alumno,
        'carreras': carreras,
        'instituciones': instituciones,
    }
    return render(request, 'cardex/editar_alumno.html', context)

@login_required
def filtrar_materias_por_carrera(request):
    """Vista AJAX para filtrar materias por carrera"""
    carrera_id = request.GET.get('carrera_id')

    if not carrera_id:
        return JsonResponse({'error': 'ID de carrera requerido'}, status=400)

    try:
        carrera = get_object_or_404(Carrera, id=carrera_id, borrado=1)
        materias = Materia.objects.filter(
            borrado=1,
            carrera=carrera
        ).order_by('semestre', 'nombre')

        materias_data = []
        for materia in materias:
            materias_data.append({
                'id': materia.id,
                'codigo': materia.codigo_materia,
                'nombre': materia.nombre,
                'semestre': materia.semestre
            })

        return JsonResponse({
            'carrera': carrera.nombre,
            'materias': materias_data
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def registrar_calificacion(request):
    """Vista para registrar calificaciones - filtra materias por carrera del alumno"""
    if request.method == 'POST':
        try:
            alumno_id = request.POST.get('alumno')
            materia_id = request.POST.get('materia')
            alumno = get_object_or_404(Alumno, id=alumno_id)
            materia = get_object_or_404(Materia, id=materia_id)

            calificacion = Calificacion(
                alumno=alumno,
                materia=materia,
                calificacion=request.POST.get('calificacion') or None,
                estado=request.POST.get('estado'),
                periodo=request.POST.get('periodo'),
                profesor=request.POST.get('profesor'),
                observaciones=request.POST.get('observaciones', '')
            )
            calificacion.save()

            messages.success(request, 'Calificación registrada exitosamente.')
            return redirect('detalle_alumno', alumno_id=alumno_id)

        except Exception as e:
            messages.error(request, f'Error al registrar calificación: {str(e)}')

    # Obtener alumno preseleccionado (si viene por GET)
    alumno_preseleccionado = None
    if request.GET.get('alumno'):
        try:
            alumno_preseleccionado = get_object_or_404(Alumno, id=request.GET.get('alumno'), borrado=1)
        except:
            pass

    # Obtener todos los alumnos
    alumnos = Alumno.objects.filter(borrado=1).select_related('carrera')

    # Filtrar materias según el alumno seleccionado
    if alumno_preseleccionado:
        # Si hay alumno preseleccionado, mostrar solo materias de su carrera
        materias = Materia.objects.filter(
            borrado=1,
            carrera=alumno_preseleccionado.carrera
        ).order_by('semestre', 'nombre')
    else:
        # Si no hay alumno preseleccionado, mostrar todas las materias
        materias = Materia.objects.filter(borrado=1).select_related('carrera').order_by('carrera__nombre', 'semestre', 'nombre')

    # Preparar datos para JavaScript (materias por carrera)
    materias_por_carrera = {}
    for materia in Materia.objects.filter(borrado=1).select_related('carrera'):
        carrera_id = str(materia.carrera.id)
        if carrera_id not in materias_por_carrera:
            materias_por_carrera[carrera_id] = []
        materias_por_carrera[carrera_id].append({
            'id': materia.id,
            'codigo': materia.codigo_materia,
            'nombre': materia.nombre,
            'semestre': materia.semestre
        })

    context = {
        'alumnos': alumnos,
        'materias': materias,
        'alumno_preseleccionado': alumno_preseleccionado,
        'materias_por_carrera_json': json.dumps(materias_por_carrera)
    }
    return render(request, 'cardex/registrar_calificacion.html', context)

@login_required
def historial_calificaciones(request):
    """Vista para ver el historial de calificaciones"""
    # Queryset base para mostrar (con filtros)
    calificaciones = Calificacion.objects.filter(
        borrado=1
    ).select_related('alumno', 'materia').order_by('-fecha_registro')

    # Filtros opcionales
    alumno_id = request.GET.get('alumno')
    materia_id = request.GET.get('materia')
    periodo = request.GET.get('periodo')
    estado = request.GET.get('estado')

    if alumno_id:
        calificaciones = calificaciones.filter(alumno_id=alumno_id)
    if materia_id:
        calificaciones = calificaciones.filter(materia_id=materia_id)
    if periodo:
        calificaciones = calificaciones.filter(periodo=periodo)
    if estado:
        # Manejar casos especiales para el filtro de estado
        if estado == 'reprobada':
            # Incluir tanto 'reprobada' como 'reprobado' para compatibilidad
            calificaciones = calificaciones.filter(estado__in=['reprobada', 'reprobado'])
        elif estado == 'aprobada':
            # Incluir tanto 'aprobada' como 'aprobado' para compatibilidad
            calificaciones = calificaciones.filter(estado__in=['aprobada', 'aprobado'])
        else:
            calificaciones = calificaciones.filter(estado=estado)

    # Estadísticas del alumno seleccionado (si hay filtro) o globales
    if alumno_id:
        # Estadísticas específicas del alumno seleccionado
        alumno_seleccionado = get_object_or_404(Alumno, id=alumno_id)
        calificaciones_alumno = Calificacion.objects.filter(
            borrado=1,
            alumno_id=alumno_id
        )
        total_calificaciones_global = calificaciones_alumno.count()
        aprobadas_global = calificaciones_alumno.filter(estado__in=['aprobada', 'aprobado']).count()
        reprobadas_global = calificaciones_alumno.filter(estado__in=['reprobada', 'reprobado']).count()
        cursando_global = calificaciones_alumno.filter(estado='cursando').count()
    else:
        # Estadísticas GLOBALES (sin filtros) - para mostrar números reales de todos los alumnos
        todas_calificaciones = Calificacion.objects.filter(borrado=1)
        total_calificaciones_global = todas_calificaciones.count()
        aprobadas_global = todas_calificaciones.filter(estado__in=['aprobada', 'aprobado']).count()
        reprobadas_global = todas_calificaciones.filter(estado__in=['reprobada', 'reprobado']).count()
        cursando_global = todas_calificaciones.filter(estado='cursando').count()

    # Estadísticas FILTRADAS (para mostrar en la tabla actual)
    total_calificaciones_filtradas = calificaciones.count()
    aprobadas_filtradas = calificaciones.filter(estado='aprobada').count()
    reprobadas_filtradas = calificaciones.filter(estado='reprobada').count()
    cursando_filtradas = calificaciones.filter(estado='cursando').count()

    alumnos = Alumno.objects.filter(borrado=1)
    materias = Materia.objects.filter(borrado=1)

    # Obtener información del alumno seleccionado para mostrar en el template
    alumno_info = None
    if alumno_id:
        try:
            alumno_obj = Alumno.objects.get(id=alumno_id, borrado=1)
            alumno_info = {
                'id': alumno_obj.id,
                'nombre_completo': alumno_obj.nombre_completo,
                'matricula': alumno_obj.matricula
            }
        except Alumno.DoesNotExist:
            pass

    context = {
        'calificaciones': calificaciones,
        'alumnos': alumnos,
        'materias': materias,
        'alumno_seleccionado': alumno_id,
        'alumno_info': alumno_info,
        'materia_seleccionada': materia_id,
        'periodo_seleccionado': periodo,
        'estado_seleccionado': estado,
        # Estadísticas globales (siempre actualizadas)
        'total_calificaciones': total_calificaciones_global,
        'aprobadas': aprobadas_global,
        'reprobadas': reprobadas_global,
        'cursando': cursando_global,
        # Estadísticas filtradas (para referencia)
        'total_calificaciones_filtradas': total_calificaciones_filtradas,
        'aprobadas_filtradas': aprobadas_filtradas,
        'reprobadas_filtradas': reprobadas_filtradas,
        'cursando_filtradas': cursando_filtradas,
    }
    return render(request, 'cardex/historial_calificaciones.html', context)

@login_required
def editar_calificacion(request, calificacion_id):
    """Vista para editar una calificación existente"""
    calificacion = get_object_or_404(Calificacion, id=calificacion_id, borrado=1)

    if request.method == 'POST':
        try:
            calificacion.calificacion = request.POST.get('calificacion') or None
            calificacion.periodo = request.POST.get('periodo')
            calificacion.profesor = request.POST.get('profesor', '')
            calificacion.observaciones = request.POST.get('observaciones', '')

            # Determinar automáticamente el estado basado en la calificación
            if calificacion.calificacion is not None:
                try:
                    calif_float = float(calificacion.calificacion)
                    if calif_float >= 7.0:
                        calificacion.estado = 'aprobada'
                    else:
                        calificacion.estado = 'reprobada'
                except (ValueError, TypeError):
                    # Si no se puede convertir a float, mantener estado actual
                    pass
            else:
                # Si no hay calificación, mantener el estado actual o establecer como cursando
                if calificacion.estado not in ['aprobada', 'reprobada']:
                    calificacion.estado = request.POST.get('estado', 'cursando')
                else:
                    calificacion.estado = request.POST.get('estado', calificacion.estado)

            calificacion.save()

            messages.success(request, 'Calificación actualizada exitosamente.')
            return redirect('historial_calificaciones')

        except Exception as e:
            messages.error(request, f'Error al actualizar calificación: {str(e)}')

    context = {
        'calificacion': calificacion,
    }
    return render(request, 'cardex/editar_calificacion.html', context)

@login_required
def gestionar_documentos_academicos(request):
    """Vista para listar documentos académicos del sistema (admin) o del usuario (alumno)"""
    is_admin = request.user.is_superuser
    
    if is_admin:
        # Admin ve todos los documentos académicos
        documentos = DocumentoAcademico.objects.filter(
            borrado=1
        ).select_related('alumno', 'alumno__usuario').order_by('-fecha_subida')
    else:
        # Usuario normal ve solo sus documentos académicos
        if hasattr(request.user, 'alumno'):
            documentos = DocumentoAcademico.objects.filter(
                alumno=request.user.alumno,
                borrado=1
            ).order_by('-fecha_subida')
        else:
            documentos = DocumentoAcademico.objects.none()
    
    # Filtros
    estado = request.GET.get('estado', '')
    tipo = request.GET.get('tipo', '')
    alumno_id = request.GET.get('alumno', '')
    
    if estado:
        documentos = documentos.filter(estado_revision=estado)
    if tipo:
        documentos = documentos.filter(tipo_documento=tipo)
    if alumno_id and is_admin:
        documentos = documentos.filter(alumno__id=alumno_id)
    
    # Obtener lista de alumnos para el filtro (solo para admin)
    alumnos = []
    if is_admin:
        alumnos = Alumno.objects.filter(borrado=1).select_related('usuario').order_by('nombre', 'apellido_paterno', 'apellido_materno')

    context = {
        'documentos': documentos,
        'es_admin': is_admin,
        'estado_seleccionado': estado,
        'tipo_seleccionado': tipo,
        'alumno_seleccionado': alumno_id,
        'alumnos': alumnos,
    }
    return render(request, 'documentos/listar_documentos_academicos.html', context)

@login_required
def revisar_documento_academico(request, documento_id):
    """Vista para revisar un documento académico específico"""
    # Solo superusuarios pueden revisar documentos
    if not request.user.is_superuser:
        messages.error(request, 'No tienes permisos para revisar documentos académicos.')
        return redirect('homeP')
    
    documento = get_object_or_404(DocumentoAcademico, id=documento_id, borrado=1)

    if request.method == 'POST':
        try:
            accion = request.POST.get('accion')
            comentarios = request.POST.get('comentarios', '')

            if accion == 'aprobar':
                documento.aprobar_documento(request.user, comentarios)
                messages.success(request, 'Documento aprobado exitosamente.')
            elif accion == 'rechazar':
                documento.rechazar_documento(request.user, comentarios)
                messages.error(request, 'Documento rechazado.')
            elif accion == 'corregir':
                documento.estado_revision = 'corregido'
                documento.revisado_por = request.user
                documento.fecha_revision = timezone.now()
                documento.comentarios_revision = comentarios
                documento.save()
                messages.warning(request, 'Documento marcado para correcciones.')

            return redirect('gestionar_documentos_academicos')

        except Exception as e:
            messages.error(request, f'Error al procesar documento: {str(e)}')

    context = {
        'documento': documento,
    }
    return render(request, 'cardex/revisar_documento.html', context)

@login_required
def editar_documento_academico(request, documento_id):
    """Vista para editar un documento académico específico"""
    documento = get_object_or_404(DocumentoAcademico, id=documento_id, borrado=1)

    # Verificar permisos: superusuarios pueden editar cualquier documento, alumnos solo los suyos
    if not request.user.is_superuser:
        # Si no es superusuario, verificar que sea el alumno propietario del documento
        if not hasattr(request.user, 'alumno') or request.user.alumno != documento.alumno:
            messages.error(request, 'No tienes permisos para editar este documento académico.')
            return redirect('detalle_alumno', alumno_id=documento.alumno.id)

    if request.method == 'POST':
        try:
            documento.titulo = request.POST.get('titulo')
            documento.descripcion = request.POST.get('descripcion', '')
            documento.tipo_documento = request.POST.get('tipo_documento')
            documento.periodo_academico = request.POST.get('periodo_academico', '')

            if request.FILES.get('archivo'):
                documento.archivo = request.FILES.get('archivo')

            documento.save()
            messages.success(request, 'Documento académico actualizado exitosamente.')
            return redirect('detalle_alumno', alumno_id=documento.alumno.id)

        except Exception as e:
            messages.error(request, f'Error al actualizar documento: {str(e)}')

    context = {
        'documento': documento,
    }
    return render(request, 'cardex/editar_documento_academico.html', context)

@login_required
def eliminar_documento_academico(request, documento_id):
    """Vista para eliminar un documento académico específico"""
    documento = get_object_or_404(DocumentoAcademico, id=documento_id)

    # Solo superusuarios pueden eliminar documentos académicos
    if not request.user.is_superuser:
        messages.error(request, 'No tienes permisos para eliminar documentos académicos.')
        return redirect('detalle_alumno', alumno_id=documento.alumno.id)

    if request.method == 'POST':
        try:
            documento.borrado = 0
            documento.save()
            messages.success(request, 'Documento académico eliminado exitosamente.')
            return redirect('gestionar_documentos_academicos')

        except Exception as e:
            messages.error(request, f'Error al eliminar documento: {str(e)}')

    context = {
        'documento': documento,
    }
    return render(request, 'cardex/eliminar_documento_academico.html', context)

@login_required
def emitir_certificado_para_documento(request, documento_id):
    """Vista para emitir un certificado en blockchain para un documento académico."""
    if not request.user.is_superuser:
        messages.error(request, "No tiene permisos para emitir certificados.")
        return redirect('dashboard_cardex')

    documento = get_object_or_404(DocumentoAcademico, id=documento_id, borrado=1)
    alumno = documento.alumno

    if documento.certificado_hash:
        messages.warning(request, "Este documento ya tiene un certificado emitido.")
        return redirect('detalle_alumno', alumno_id=alumno.id)

    if request.method == 'POST':
        try:
            # Usamos el ID del documento como ID único para el certificado.
            cert_id = documento.id

            # Llamamos a la función del contrato inteligente
            receipt = contrato.emitir_certificado(
                id=cert_id,
                nombre=alumno.nombre,
                ap_paterno=alumno.apellido_paterno,
                ap_materno=alumno.apellido_materno,
                matricula=alumno.matricula,
                curso=documento.titulo,  # Usamos el título del documento como el "curso"
                fecha=timezone.now().strftime("%d/%m/%Y")
            )

            # Guardamos la información del certificado en el documento
            documento.certificado_id = str(cert_id)
            documento.certificado_hash = receipt.get('hash')
            documento.fecha_emision_certificado = timezone.now()
            documento.save()

            messages.success(request, f"Certificado para '{documento.titulo}' emitido con éxito. Hash: {receipt.get('hash')}")
        except Exception as e:
            messages.error(request, f"Error al emitir el certificado: {str(e)}")
    return redirect('detalle_alumno', alumno_id=alumno.id)

@login_required
def verificar_certificado_blockchain(request):
    """
    Vista para verificar un certificado en la blockchain usando su hash de transacción.
    """
    tx_hash = request.GET.get('hash', None)
    receipt = None
    error = None

    if tx_hash:
        try:
            # Validar que el hash tenga el formato correcto (0x seguido de 64 caracteres hexadecimales)
            if not tx_hash:
                raise ValueError("No se proporcionó ningún hash de transacción.")
            
            if not tx_hash.startswith('0x'):
                raise ValueError("El hash de transacción debe empezar con '0x'. Formato esperado: 0x seguido de 64 caracteres hexadecimales.")
            
            if len(tx_hash) != 66:
                raise ValueError(f"El hash de transacción debe tener exactamente 66 caracteres (incluyendo '0x'). Longitud actual: {len(tx_hash)} caracteres.")
            
            # Verificar que solo contenga caracteres hexadecimales después del 0x
            hex_part = tx_hash[2:]
            if not all(c in '0123456789abcdefABCDEF' for c in hex_part):
                raise ValueError("El hash de transacción contiene caracteres no válidos. Solo se permiten caracteres hexadecimales (0-9, a-f, A-F).")

            receipt = contrato.verificar_transaccion(tx_hash)
            if receipt:
                messages.success(request, f"Transacción encontrada en la blockchain.")
            else:
                error = f"No se encontró ninguna transacción con el hash proporcionado."
                messages.error(request, error)
        except ValueError as ve:
            error = str(ve)
            messages.error(request, error)
        except Exception as e:
            error = f"Ocurrió un error al verificar la transacción: {str(e)}"
            messages.error(request, error)

    context = {
        'tx_hash': tx_hash,
        'receipt': receipt,
        'error': error,
    }
    return render(request, 'cardex/verificar_certificado.html', context)
# ==================== VISTAS PARA ADMINISTRACIÓN ====================

@login_required
def gestionar_catalogos(request):
    """Vista que sirve como hub para los diferentes catálogos del sistema."""
    if not request.user.is_superuser:
        messages.error(request, "Acceso denegado. Solo los administradores pueden acceder a esta página.")
        return redirect('homeP')

    # Esta vista simplemente renderiza un template que contiene los enlaces a los demás catálogos.
    return render(request, 'admin/catalogos.html')


@login_required
def gestionar_perfiles(request):
    """Vista para gestionar perfiles/roles de usuario."""
    if not request.user.is_superuser:
        messages.error(request, "Acceso denegado.")
        return redirect('homeP')

    if request.method == 'POST':
        try:
            accion = request.POST.get('accion')

            if accion == 'crear':
                nombre_perfil = request.POST.get('nombre')
                if nombre_perfil and not ct_perfil.objects.filter(nombre=nombre_perfil, borrado=1).exists():
                    ct_perfil.objects.create(nombre=nombre_perfil)
                    messages.success(request, f'Perfil "{nombre_perfil}" creado exitosamente.')
                else:
                    messages.error(request, 'El nombre del perfil no puede estar vacío o ya existe.')

            elif accion == 'editar':
                perfil_id = request.POST.get('perfil_id')
                nuevo_nombre = request.POST.get('nombre')
                perfil = get_object_or_404(ct_perfil, id=perfil_id)
                if nuevo_nombre and not ct_perfil.objects.filter(nombre=nuevo_nombre, borrado=1).exclude(id=perfil_id).exists():
                    perfil.nombre = nuevo_nombre
                    perfil.save()
                    messages.success(request, 'Perfil actualizado exitosamente.')
                else:
                    messages.error(request, 'El nombre del perfil no puede estar vacío o ya existe.')

        except Exception as e:
            messages.error(request, f'Error al procesar la solicitud: {str(e)}')
        return redirect('gestionar_perfiles')

    perfiles = ct_perfil.objects.filter(borrado=1).prefetch_related(
        models.Prefetch(
            'permiso_set',
            queryset=Permiso.objects.filter(puede_leer=True).select_related('modulo'),
            to_attr='permisos_con_acceso'
        )
    ).order_by('nombre')
    context = {
        'perfiles': perfiles,
    }
    return render(request, 'admin/gestionar_perfiles.html', context)


@login_required
def desactivar_perfil(request, perfil_id):
    """Vista para desactivar (borrado lógico) un perfil."""
    if not request.user.is_superuser:
        messages.error(request, "Acceso denegado.")
        return redirect('homeP')

    if request.method == 'POST':
        try:
            perfil = get_object_or_404(ct_perfil, id=perfil_id)
            perfil.borrado = 0
            perfil.save()
            messages.success(request, f'Perfil "{perfil.nombre}" desactivado exitosamente.')
        except Exception as e:
            messages.error(request, f'Error al desactivar el perfil: {str(e)}')
    return redirect('gestionar_perfiles')


@login_required
def gestionar_permisos_perfil(request, perfil_id):
    """Vista para asignar permisos de módulos a un perfil específico."""
    if not request.user.is_superuser:
        messages.error(request, "Acceso denegado.")
        return redirect('homeP')

    # Módulos predefinidos del sistema. Se crearán si no existen.
    modulos_sistema = [
        {'nombre': 'Gestión de Alumnos', 'clave': 'alumnos', 'url': '/alumnos/'},
        {'nombre': 'Gestión de Documentos', 'clave': 'documentos', 'url': '/documentos/'},
        {'nombre': 'Gestión de Calificaciones', 'clave': 'calificaciones', 'url': '/calificaciones/historial/'},
        {'nombre': 'Administración de Catálogos', 'clave': 'catalogos', 'url': '/admin/catalogos/'},
        {'nombre': 'Perfiles y Permisos', 'clave': 'perfiles', 'url': '/admin/perfiles/'},
        {'nombre': 'Gestión de Usuarios', 'clave': 'usuarios', 'url': '/admin/usuarios/'},
    ]
    for mod_data in modulos_sistema:
        ct_modulos.objects.get_or_create(
            clave=mod_data['clave'],
            defaults={'nombre': mod_data['nombre'], 'url': mod_data['url']}
        )

    perfil = get_object_or_404(ct_perfil, id=perfil_id, borrado=1)
    modulos = ct_modulos.objects.filter(borrado=1).order_by('nombre')

    if request.method == 'POST':
        try:
            with transaction.atomic():
                for modulo in modulos:
                    puede_leer = f'permiso_{modulo.id}_leer' in request.POST
                    puede_crear = f'permiso_{modulo.id}_crear' in request.POST
                    puede_actualizar = f'permiso_{modulo.id}_actualizar' in request.POST
                    puede_eliminar = f'permiso_{modulo.id}_eliminar' in request.POST

                    Permiso.objects.update_or_create(
                        perfil=perfil,
                        modulo=modulo,
                        defaults={
                            'puede_leer': puede_leer,
                            'puede_crear': puede_crear,
                            'puede_actualizar': puede_actualizar,
                            'puede_eliminar': puede_eliminar,
                        }
                    )
            messages.success(request, f'Permisos para el perfil "{perfil.nombre}" actualizados correctamente.')
            return redirect('gestionar_perfiles')
        except Exception as e:
            messages.error(request, f'Error al actualizar los permisos: {str(e)}')

    permisos_actuales = {p.modulo.id: p for p in Permiso.objects.filter(perfil=perfil)}
    modulos_con_permisos = [{'modulo': m, 'permiso': permisos_actuales.get(m.id)} for m in modulos]

    context = {'perfil': perfil, 'modulos_con_permisos': modulos_con_permisos}
    return render(request, 'admin/gestionar_permisos_perfil.html', context)

@login_required
def gestionar_categorias_documentos(request):
    """Vista para gestionar categorías de documentos"""
    if request.method == 'POST':
        try:
            accion = request.POST.get('accion')

            if accion == 'crear':
                categoria = CategoriaDocumento(
                    nombre=request.POST.get('nombre'),
                    descripcion=request.POST.get('descripcion', ''),
                    tipo=request.POST.get('tipo')
                )
                categoria.save()
                messages.success(request, 'Categoría creada exitosamente.')

            elif accion == 'editar':
                categoria_id = request.POST.get('categoria_id')
                categoria = get_object_or_404(CategoriaDocumento, id=categoria_id)
                categoria.nombre = request.POST.get('nombre')
                categoria.descripcion = request.POST.get('descripcion', '')
                categoria.tipo = request.POST.get('tipo')
                categoria.save()
                messages.success(request, 'Categoría actualizada exitosamente.')

            elif accion == 'eliminar':
                categoria_id = request.POST.get('categoria_id')
                categoria = get_object_or_404(CategoriaDocumento, id=categoria_id)
                categoria.borrado = 0
                categoria.save()
                messages.success(request, 'Categoría eliminada exitosamente.')

        except Exception as e:
            messages.error(request, f'Error al procesar la solicitud: {str(e)}')

    categorias = CategoriaDocumento.objects.filter(borrado=1).order_by('tipo', 'nombre')
    return render(request, 'admin/categorias_documentos.html', {'categorias': categorias})

@login_required
def gestionar_materias(request):
    """Vista para gestionar materias con filtros por carrera y semestre"""
    if request.method == 'POST':
        try:
            carrera_id = request.POST.get('carrera')
            carrera = get_object_or_404(Carrera, id=carrera_id)

            materia = Materia(
                codigo_materia=request.POST.get('codigo_materia'),
                nombre=request.POST.get('nombre'),
                descripcion=request.POST.get('descripcion', ''),
                carrera=carrera,
                semestre=request.POST.get('semestre'),
                creditos=request.POST.get('creditos', 0)
            )
            materia.save()
            messages.success(request, 'Materia creada exitosamente.')
        except Exception as e:
            messages.error(request, f'Error al crear materia: {str(e)}')

    # Obtener filtros de la URL
    carrera_id = request.GET.get('carrera')
    semestre = request.GET.get('semestre')

    # Base queryset para materias
    materias = Materia.objects.filter(borrado=1).select_related('carrera')

    # Aplicar filtros
    if carrera_id:
        materias = materias.filter(carrera_id=carrera_id)
    if semestre:
        materias = materias.filter(semestre=semestre)

    # Obtener todas las carreras para el filtro
    carreras = Carrera.objects.filter(borrado=1)

    # Obtener semestres disponibles (1-12)
    semestres_disponibles = range(1, 13)

    # Estadísticas por carrera (si hay filtro de carrera)
    estadisticas_carrera = None
    if carrera_id:
        carrera_seleccionada = get_object_or_404(Carrera, id=carrera_id)
        total_materias_carrera = Materia.objects.filter(
            borrado=1,
            carrera_id=carrera_id
        ).count()

        # Créditos totales por semestre
        creditos_por_semestre = {}
        for sem in range(1, 13):
            creditos = Materia.objects.filter(
                borrado=1,
                carrera_id=carrera_id,
                semestre=sem
            ).aggregate(total=Sum('creditos'))['total'] or 0
            if creditos > 0:
                creditos_por_semestre[sem] = creditos

        estadisticas_carrera = {
            'carrera': carrera_seleccionada,
            'total_materias': total_materias_carrera,
            'creditos_por_semestre': creditos_por_semestre,
            'total_creditos': sum(creditos_por_semestre.values())
        }

    context = {
        'carreras': carreras,
        'materias': materias,
        'carrera_seleccionada': carrera_id,
        'semestre_seleccionado': semestre,
        'semestres_disponibles': semestres_disponibles,
        'estadisticas_carrera': estadisticas_carrera,
        'total_materias_filtradas': materias.count()
    }
    return render(request, 'admin/materias.html', context)

# ==================== VISTAS PARA GESTIÓN DE CARRERAS ====================

@login_required
def gestionar_carreras_admin(request):
    """Vista para gestionar carreras académicas (similar a categorías de productos)"""
    if request.method == 'POST':
        try:
            carrera_id = request.POST.get('carrera_id')
            if carrera_id:
                # Editar carrera existente
                carrera = get_object_or_404(Carrera, id=carrera_id)
                carrera.nombre = request.POST.get('nombre')
                carrera.descripcion = request.POST.get('descripcion', '')
                carrera.codigo_carrera = request.POST.get('codigo_carrera')
                carrera.save()
                messages.success(request, 'Carrera actualizada exitosamente.')
            else:
                # Crear nueva carrera
                carrera = Carrera(
                    nombre=request.POST.get('nombre'),
                    descripcion=request.POST.get('descripcion', ''),
                    codigo_carrera=request.POST.get('codigo_carrera')
                )
                carrera.save()
                messages.success(request, 'Carrera creada exitosamente.')
        except Exception as e:
            messages.error(request, f'Error al procesar carrera: {str(e)}')

    carreras = Carrera.objects.filter(borrado=1)
    return render(request, 'admin/carreras_admin.html', {'carreras': carreras})

@login_required
def desactivar_carrera(request, carrera_id):
    """Vista para desactivar una carrera académica"""
    if request.method == 'POST':
        try:
            carrera = get_object_or_404(Carrera, id=carrera_id, borrado=1)
            carrera.borrado = 0
            carrera.save()
            messages.success(request, f'Carrera "{carrera.nombre}" desactivada exitosamente.')
        except Exception as e:
            messages.error(request, f'Error al desactivar carrera: {str(e)}')
    return redirect('gestionar_carreras_admin')

@login_required
def activar_carrera(request, carrera_id):
    """Vista para activar una carrera académica"""
    if request.method == 'POST':
        try:
            carrera = get_object_or_404(Carrera, id=carrera_id, borrado=0)
            carrera.borrado = 1
            carrera.save()
            messages.success(request, f'Carrera "{carrera.nombre}" activada exitosamente.')
        except Exception as e:
            messages.error(request, f'Error al activar carrera: {str(e)}')
    return redirect('gestionar_carreras_admin')

@login_required
def eliminar_carrera(request, carrera_id):
    """Vista para eliminar permanentemente una carrera académica (solo administradores)"""
    if not request.user.is_superuser:
        messages.error(request, 'No tienes permisos para eliminar carreras permanentemente.')
        return redirect('gestionar_carreras_admin')

    if request.method == 'POST':
        try:
            carrera = get_object_or_404(Carrera, id=carrera_id)
            nombre_carrera = carrera.nombre
            carrera.delete()  # Eliminación permanente
            messages.success(request, f'Carrera "{nombre_carrera}" eliminada permanentemente.')
        except Exception as e:
            messages.error(request, f'Error al eliminar carrera: {str(e)}')
    return redirect('gestionar_carreras_admin')

@login_required
def gestionar_usuarios(request):
    """Vista para gestionar usuarios, asignarles perfiles y roles."""
    if not request.user.is_superuser:
        messages.error(request, "Acceso denegado.")
        return redirect('homeP')

    if request.method == 'POST':
        try:
            usuario_id = request.POST.get('usuario_id')
            perfil_id = request.POST.get('perfil')
            usuario = get_object_or_404(User, id=usuario_id)
            tb_usuario, created = tb_usaurios.objects.get_or_create(id_user_fk=usuario)

            if perfil_id:
                perfil = get_object_or_404(ct_perfil, id=perfil_id, borrado=1)
                tb_usuario.perfil_fk = perfil
            else:
                tb_usuario.perfil_fk = None

            tb_usuario.save()
            messages.success(request, f'Perfil para el usuario "{usuario.username}" actualizado correctamente.')
        except Exception as e:
            messages.error(request, f'Error al asignar perfil: {str(e)}')
        return redirect('gestionar_usuarios')

    usuarios = User.objects.select_related('perfil_usuario__perfil_fk').filter(is_active=True).order_by('username')
    perfiles = ct_perfil.objects.filter(borrado=1).order_by('nombre')

    context = {
        'usuarios': usuarios,
        'perfiles': perfiles,
    }
    return render(request, 'admin/gestionar_usuarios.html', context)


@login_required
def cambiar_password_usuario(request, usuario_id):
    """Vista para que un admin cambie la contraseña de otro usuario."""
    if not request.user.is_superuser:
        messages.error(request, "Acceso denegado.")
        return redirect('homeP')

    if request.method == 'POST':
        usuario_a_cambiar = get_object_or_404(User, id=usuario_id)
        nueva_password = request.POST.get('nueva_password')
        confirmar_password = request.POST.get('confirmar_password')

        if nueva_password and nueva_password == confirmar_password:
            if len(nueva_password) >= 8:
                usuario_a_cambiar.password = make_password(nueva_password)
                usuario_a_cambiar.save()
                messages.success(request, f"La contraseña del usuario '{usuario_a_cambiar.username}' ha sido actualizada.")
            else:
                messages.error(request, "La contraseña debe tener al menos 8 caracteres.")
        else:
            messages.error(request, "Las contraseñas no coinciden o están vacías.")
    
    return redirect('gestionar_usuarios')

@login_required
def crear_usuario(request):
    """Vista para que un admin cree un nuevo usuario."""
    if not request.user.is_superuser:
        messages.error(request, "Acceso denegado.")
        return redirect('homeP')

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirmar_password = request.POST.get('confirmar_password')
        perfil_id = request.POST.get('perfil')

        # Validaciones
        if not username or not password:
            messages.error(request, "El usuario y la contraseña son requeridos.")
            return redirect('crear_usuario')

        if password != confirmar_password:
            messages.error(request, "Las contraseñas no coinciden.")
            return redirect('crear_usuario')

        if len(password) < 8:
            messages.error(request, "La contraseña debe tener al menos 8 caracteres.")
            return redirect('crear_usuario')

        if User.objects.filter(username=username).exists():
            messages.error(request, f"El usuario '{username}' ya existe.")
            return redirect('crear_usuario')

        try:
            # Crear el usuario
            nuevo_usuario = User.objects.create_user(
                username=username,
                email=email or '',
                password=password
            )
            
            # Asignar perfil si es proporcionado
            if perfil_id:
                perfil = get_object_or_404(ct_perfil, id=perfil_id, borrado=1)
                tb_usuario, created = tb_usaurios.objects.get_or_create(id_user_fk=nuevo_usuario)
                tb_usuario.perfil_fk = perfil
                tb_usuario.save()
            
            messages.success(request, f"Usuario '{username}' creado exitosamente.")
            return redirect('gestionar_usuarios')
        except Exception as e:
            messages.error(request, f"Error al crear el usuario: {str(e)}")
            return redirect('crear_usuario')

    perfiles = ct_perfil.objects.filter(borrado=1).order_by('nombre')
    context = {'perfiles': perfiles}
    return render(request, 'admin/crear_usuario.html', context)

@login_required
def eliminar_usuario(request, usuario_id):
    """Vista para que un admin elimine (desactive) un usuario."""
    if not request.user.is_superuser:
        messages.error(request, "Acceso denegado.")
        return redirect('homeP')

    usuario = get_object_or_404(User, id=usuario_id)
    
    # No permitir eliminar el propio usuario
    if usuario == request.user:
        messages.error(request, "No puedes desactivar tu propia cuenta.")
        return redirect('gestionar_usuarios')

    # No permitir eliminar otros superusuarios
    if usuario.is_superuser:
        messages.error(request, "No puedes desactivar a otros administradores.")
        return redirect('gestionar_usuarios')

    try:
        usuario.is_active = False
        usuario.save()
        messages.success(request, f"Usuario '{usuario.username}' desactivado exitosamente.")
    except Exception as e:
        messages.error(request, f"Error al desactivar el usuario: {str(e)}")
    
    return redirect('gestionar_usuarios')

@login_required
def reactivar_usuario(request, usuario_id):
    """Vista para que un admin reactive un usuario desactivado."""
    if not request.user.is_superuser:
        messages.error(request, "Acceso denegado.")
        return redirect('homeP')

    usuario = get_object_or_404(User, id=usuario_id)

    try:
        usuario.is_active = True
        usuario.save()
        messages.success(request, f"Usuario '{usuario.username}' reactivado exitosamente.")
    except Exception as e:
        messages.error(request, f"Error al reactivar el usuario: {str(e)}")
    
    return redirect('gestionar_usuarios')

@login_required
def editar_usuario(request, usuario_id):
    """Vista para que un admin edite la información de un usuario."""
    if not request.user.is_superuser:
        messages.error(request, "Acceso denegado.")
        return redirect('homeP')

    usuario = get_object_or_404(User, id=usuario_id)

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        perfil_id = request.POST.get('perfil')
        mostrar_menu_rapido = request.POST.get('mostrar_menu_rapido') == 'on'

        try:
            usuario.email = email
            usuario.first_name = first_name
            usuario.last_name = last_name
            usuario.save()

            # Obtener o crear el perfil de usuario
            tb_usuario, created = tb_usaurios.objects.get_or_create(id_user_fk=usuario)
            
            # Actualizar perfil si se proporciona
            if perfil_id:
                perfil = get_object_or_404(ct_perfil, id=perfil_id, borrado=1)
                tb_usuario.perfil_fk = perfil
            
            # Actualizar control de menú rápido
            tb_usuario.mostrar_menu_rapido = mostrar_menu_rapido
            tb_usuario.save()

            messages.success(request, f"Usuario '{usuario.username}' actualizado exitosamente.")
            return redirect('gestionar_usuarios')
        except Exception as e:
            messages.error(request, f"Error al actualizar el usuario: {str(e)}")

    perfiles = ct_perfil.objects.filter(borrado=1).order_by('nombre')
    tb_usuario, created = tb_usaurios.objects.get_or_create(id_user_fk=usuario)
    context = {
        'usuario': usuario,
        'tb_usuario': tb_usuario,
        'perfiles': perfiles,
    }
    return render(request, 'admin/editar_usuario.html', context)

@login_required
def historial_usuarios(request):
    """Vista para ver el historial de cambios de usuarios."""
    if not request.user.is_superuser:
        messages.error(request, "Acceso denegado.")
        return redirect('homeP')

    # Obtener todos los usuarios con información de cuándo fueron creados y modificados
    usuarios = User.objects.all().order_by('-date_joined')
    
    context = {
        'usuarios': usuarios,
    }
    return render(request, 'admin/historial_usuarios.html', context)

@login_required
def gestionar_usuarios_mejorado(request):
    """Vista mejorada para gestionar usuarios con búsqueda y filtrado."""
    if not request.user.is_superuser:
        messages.error(request, "Acceso denegado.")
        return redirect('homeP')

    # Obtener parámetros de búsqueda y filtrado
    buscar = request.GET.get('buscar', '').strip()
    filtro_estado = request.GET.get('estado', '')  # 'activo', 'inactivo', 'todos'

    # Empezar con todos los usuarios
    usuarios = User.objects.all().order_by('username')

    # Aplicar búsqueda
    if buscar:
        usuarios = usuarios.filter(
            models.Q(username__icontains=buscar) |
            models.Q(email__icontains=buscar) |
            models.Q(first_name__icontains=buscar) |
            models.Q(last_name__icontains=buscar)
        )

    # Aplicar filtro de estado
    if filtro_estado == 'activo':
        usuarios = usuarios.filter(is_active=True)
    elif filtro_estado == 'inactivo':
        usuarios = usuarios.filter(is_active=False)

    perfiles = ct_perfil.objects.filter(borrado=1).order_by('nombre')

    context = {
        'usuarios': usuarios,
        'perfiles': perfiles,
        'buscar': buscar,
        'filtro_estado': filtro_estado,
    }
    return render(request, 'admin/gestionar_usuarios.html', context)

@login_required
def exportar_usuarios_csv(request):
    """Vista para exportar usuarios a CSV."""
    if not request.user.is_superuser:
        messages.error(request, "Acceso denegado.")
        return redirect('homeP')

    import csv
    from django.http import HttpResponse

    # Crear respuesta CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="usuarios.csv"'

    writer = csv.writer(response, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    
    # Encabezados
    writer.writerow(['ID', 'Usuario', 'Correo', 'Nombre', 'Apellido', 'Perfil', 'Estado', 'Fecha Creación', 'Fecha Última Modificación', 'Es Admin'])

    # Datos de usuarios
    usuarios = User.objects.all().order_by('username')
    
    for usuario in usuarios:
        perfil = 'Sin Perfil'
        if hasattr(usuario, 'perfil_usuario') and usuario.perfil_usuario.perfil_fk:
            perfil = usuario.perfil_usuario.perfil_fk.nombre

        estado = 'Activo' if usuario.is_active else 'Inactivo'
        es_admin = 'Sí' if usuario.is_superuser else 'No'

        writer.writerow([
            usuario.id,
            usuario.username,
            usuario.email,
            usuario.first_name,
            usuario.last_name,
            perfil,
            estado,
            usuario.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
            usuario.last_login.strftime('%Y-%m-%d %H:%M:%S') if usuario.last_login else 'Nunca',
            es_admin,
        ])

    messages.success(request, "Usuarios exportados exitosamente.")
    return response

@login_required
def configurar_cuenta_admin(request):
    """Vista para que el administrador configure su propia cuenta."""
    if not request.user.is_superuser:
        messages.error(request, "Acceso denegado.")
        return redirect('homeP')

    if request.method == 'POST':
        try:
            correo = request.POST.get('correo')
            nueva_password = request.POST.get('nueva_password')
            confirmar_password = request.POST.get('confirmar_password')

            request.user.email = correo

            if nueva_password and nueva_password == confirmar_password:
                if len(nueva_password) >= 8:
                    request.user.password = make_password(nueva_password)
                    messages.success(request, "La contraseña ha sido actualizada.")
                else:
                    messages.error(request, "La contraseña debe tener al menos 8 caracteres.")
            elif nueva_password or confirmar_password:
                messages.error(request, "Las contraseñas no coinciden.")

            request.user.save()
            messages.success(request, "Información de la cuenta actualizada correctamente.")
        except Exception as e:
            messages.error(request, f'Error al actualizar la información de la cuenta: {str(e)}')
        return redirect('configurar_cuenta_admin')

    context = {
        'usuario': request.user,
    }
    return render(request, 'admin/configurar_cuenta_admin.html', context)

    return redirect('gestionar_usuarios')


@login_required
def dashboard_jefatura(request):
    """Dashboard para Jefatura de División: muestra acciones disponibles según permisos del perfil."""
    # Verificar que el usuario tenga un perfil y permisos
    if not hasattr(request.user, 'perfil_usuario') or not request.user.perfil_usuario.perfil_fk:
        messages.error(request, 'No tienes un perfil asignado.')
        return redirect('homeP')

    tb_usuario = request.user.perfil_usuario

    # Obtener permisos por módulo (ejemplos de claves: 'alumnos', 'documentos_personales', 'documentos_academicos')
    permisos = {
        'ver_alumnos': tb_usuario.tiene_permiso('alumnos', 'leer'),
        'gestionar_documentos_personales': tb_usuario.tiene_permiso('documentos_personales', 'leer'),
        'gestionar_documentos_academicos': tb_usuario.tiene_permiso('documentos_academicos', 'leer'),
        'registrar_calificaciones': tb_usuario.tiene_permiso('calificaciones', 'crear'),
    }

    # Recolectar datos útiles para la jefatura
    total_alumnos = Alumno.objects.filter(borrado=1).count() if permisos['ver_alumnos'] else 0
    documentos_pendientes = DocumentoAcademico.objects.filter(estado_revision='pendiente', borrado=1).count() if permisos['gestionar_documentos_academicos'] else 0

    context = {
        'permisos': permisos,
        'total_alumnos': total_alumnos,
        'documentos_pendientes': documentos_pendientes,
    }

    return render(request, 'jefatura/dashboard.html', context)


@login_required
def jefatura_panel(request):
    """Panel principal para Jefatura de División. Acceso: superuser o perfil Jefatura de División."""
    # La función _es_jefatura ya centraliza la lógica de permisos.
    if not _es_jefatura(request.user):
        messages.error(request, 'No tienes permiso para acceder al panel de Jefatura.')
        return redirect('homeP')
    
    # --- Estadísticas para el panel de Jefatura ---
    
    # 1. Total de alumnos activos
    total_alumnos = Alumno.objects.filter(borrado=1, estado='activo').count()
    
    # 2. Documentos pendientes de revisión (académicos y personales)
    docs_academicos_pendientes = DocumentoAcademico.objects.filter(borrado=1, estado_revision='pendiente').count()
    docs_personales_pendientes = DocumentoPersonal.objects.filter(borrado=1, estado='pendiente').count()
    total_documentos_pendientes = docs_academicos_pendientes + docs_personales_pendientes
    
    # 3. Alumnos con bajo promedio (ej: < 7.0)
    alumnos_bajo_promedio = []
    alumnos = Alumno.objects.filter(borrado=1, estado='activo').select_related('carrera')
    for alumno in alumnos:
        promedio = alumno.promedio_general
        if promedio > 0 and promedio < 7.0:
            alumnos_bajo_promedio.append(alumno)
    
    # 4. Últimos documentos subidos
    ultimos_documentos = DocumentoAcademico.objects.filter(borrado=1).select_related('alumno').order_by('-fecha_subida')[:10]

    # 5. Estadísticas adicionales
    total_carreras = Carrera.objects.filter(borrado=1).count()
    
    hoy = timezone.now().date()
    documentos_hoy = DocumentoAcademico.objects.filter(
        borrado=1,
        fecha_subida__date=hoy
    ).count()

    context = {
        'usuario': request.user,
        'total_alumnos': total_alumnos,
        'total_documentos_pendientes': total_documentos_pendientes,
        'total_alumnos_bajo_promedio': len(alumnos_bajo_promedio),
        'lista_alumnos_bajo_promedio': alumnos_bajo_promedio[:5],
        'ultimos_documentos': ultimos_documentos,
        'total_carreras': total_carreras,
        'documentos_hoy': documentos_hoy,
    }
    return render(request, 'jefatura/panel.html', context)


def _es_jefatura(user):
    """Helper: devuelve True si el user es superuser o tiene perfil Jefatura de División."""
    if hasattr(user, 'perfil_usuario') and user.perfil_usuario.perfil_fk:
        nombre = user.perfil_usuario.perfil_fk.nombre.strip().lower()
        return nombre == 'jefatura de división' or nombre == 'jefatura de division' or 'jefatura' in nombre
    return False

def _es_control_escolar(user):
    """Helper: devuelve True si el user tiene perfil Control Escolar."""
    if hasattr(user, 'perfil_usuario') and user.perfil_usuario.perfil_fk:
        nombre = user.perfil_usuario.perfil_fk.nombre.strip().lower()
        return ('control' in nombre and 'escolar' in nombre) or 'control_escolar' in nombre
    return False

def _es_profesor(user):
    """Helper: devuelve True si el user tiene perfil Profesor/Maestro."""
    if hasattr(user, 'perfil_usuario') and user.perfil_usuario.perfil_fk:
        nombre = user.perfil_usuario.perfil_fk.nombre.strip().lower()
        return 'profesor' in nombre or 'maestro' in nombre or 'docente' in nombre
    return False

@login_required
def profesor_panel(request):
    """Panel principal para Profesores."""
    if not _es_profesor(request.user):
        messages.error(request, 'No tienes permiso para acceder al panel de Profesor.')
        return redirect('homeP')
    
    context = {
        'usuario': request.user,
        'fecha_actual': timezone.now()
    }
    return render(request, 'profesor/panel.html', context)

@login_required
def control_escolar_panel(request):
    """Panel principal para Control Escolar."""
    if not _es_control_escolar(request.user):
        messages.error(request, 'No tienes permiso para acceder al panel de Control Escolar.')
        return redirect('homeP')
    
    # Estadísticas para Control Escolar (similares a Jefatura)
    total_alumnos = Alumno.objects.filter(borrado=1, estado='activo').count()
    
    docs_academicos_pendientes = DocumentoAcademico.objects.filter(borrado=1, estado_revision='pendiente').count()
    docs_personales_pendientes = DocumentoPersonal.objects.filter(borrado=1, estado='pendiente').count()
    total_documentos_pendientes = docs_academicos_pendientes + docs_personales_pendientes
    
    alumnos_bajo_promedio = []
    alumnos = Alumno.objects.filter(borrado=1, estado='activo').select_related('carrera')
    for alumno in alumnos:
        promedio = alumno.promedio_general
        if promedio > 0 and promedio < 7.0:
            alumnos_bajo_promedio.append(alumno)
    
    ultimos_documentos = DocumentoAcademico.objects.filter(borrado=1).select_related('alumno').order_by('-fecha_subida')[:10]
    documentos_hoy = DocumentoAcademico.objects.filter(borrado=1, fecha_subida__date=timezone.now().date()).count()

    context = {
        'usuario': request.user,
        'total_alumnos': total_alumnos,
        'total_documentos_pendientes': total_documentos_pendientes,
        'total_alumnos_bajo_promedio': len(alumnos_bajo_promedio),
        'lista_alumnos_bajo_promedio': alumnos_bajo_promedio[:5],
        'ultimos_documentos': ultimos_documentos,
        'documentos_hoy': documentos_hoy,
    }
    return render(request, 'control_escolar/panel.html', context)

@login_required
def jefatura_lista_alumnos(request):
    """Lista de alumnos accesible solo por Jefatura de División."""
    if not _es_jefatura(request.user):
        messages.error(request, 'No tienes permiso para acceder a esta sección.')
        return redirect('homeP')

    alumnos = Alumno.objects.filter(borrado=1).select_related('usuario', 'carrera').order_by('nombre_completo')

    context = {
        'alumnos': alumnos,
    }
    return render(request, 'jefatura/alumnos_list.html', context)

# ==================== VISTAS PARA GESTIÓN DE INSTITUCIONES ====================

@login_required
def gestionar_instituciones_procedencia(request):
    """Vista para gestionar instituciones de procedencia"""
    if request.method == 'POST':
        try:
            institucion = InstitucionProcedencia(
                nombre=request.POST.get('nombre'),
                tipo_institucion=request.POST.get('tipo_institucion'),
                ciudad=request.POST.get('ciudad', ''),
                estado=request.POST.get('estado', ''),
                pais=request.POST.get('pais', 'México'),
                clave_institucion=request.POST.get('clave_institucion', ''),
                descripcion=request.POST.get('descripcion', '')
            )
            institucion.save()
            messages.success(request, 'Institución creada exitosamente.')
        except Exception as e:
            messages.error(request, f'Error al crear institución: {str(e)}')

    instituciones = InstitucionProcedencia.objects.filter(borrado=1)
    return render(request, 'admin/instituciones_procedencia.html', {'instituciones': instituciones})

# ==================== VISTAS PARA DOCUMENTOS ACADÉMICOS ====================

@login_required
def listar_documentos_academicos(request):
    """Vista para listar documentos académicos del usuario logueado o todos si es admin"""
    is_admin = request.user.is_superuser
    
    if is_admin:
        # Admin ve todos los documentos académicos
        documentos = DocumentoAcademico.objects.filter(borrado=1).select_related('alumno', 'alumno__usuario').order_by('-fecha_subida')
    else:
        # Usuario normal ve solo sus documentos académicos
        if hasattr(request.user, 'alumno'):
            documentos = DocumentoAcademico.objects.filter(alumno=request.user.alumno, borrado=1).order_by('-fecha_subida')
        else:
            documentos = DocumentoAcademico.objects.none()
    
    context = {
        'documentos': documentos,
        'es_admin': is_admin,
    }
    return render(request, 'documentos/listar_documentos_academicos.html', context)

@login_required
def listar_documentos_titulacion(request):
    """Vista para listar documentos de titulación del usuario logueado o todos si es admin"""
    is_admin = request.user.is_superuser
    
    if is_admin:
        # Admin ve todos los documentos de titulación
        documentos = DocumentoAcademico.objects.filter(
            borrado=1,
            tipo_documento__in=['titulo', 'cedula', 'acta_examen', 'liberacion_ss', 'otro']
        ).select_related('alumno', 'alumno__usuario').order_by('-fecha_subida')
    else:
        # Usuario normal ve solo sus documentos de titulación
        if hasattr(request.user, 'alumno'):
            documentos = DocumentoAcademico.objects.filter(
                alumno=request.user.alumno,
                borrado=1,
                tipo_documento__in=['titulo', 'cedula', 'acta_examen', 'liberacion_ss', 'otro']
            ).order_by('-fecha_subida')
        else:
            documentos = DocumentoAcademico.objects.none()
    
    # Filtros
    estado = request.GET.get('estado', '')
    tipo = request.GET.get('tipo', '')
    alumno_id = request.GET.get('alumno', '')
    
    if estado:
        documentos = documentos.filter(estado_revision=estado)
    
    if tipo:
        documentos = documentos.filter(tipo_documento=tipo)
    
    if alumno_id and is_admin:
        documentos = documentos.filter(alumno__id=alumno_id)
    
    # Obtener lista de alumnos para el filtro (solo para admin)
    alumnos = []
    if is_admin:
        alumnos = Alumno.objects.filter(borrado=1).select_related('usuario').order_by('nombre', 'apellido_paterno', 'apellido_materno')
    
    context = {
        'documentos': documentos,
        'es_admin': is_admin,
        'estado_seleccionado': estado,
        'tipo_seleccionado': tipo,
        'alumno_seleccionado': alumno_id,
        'alumnos': alumnos,
    }
    return render(request, 'documentos/listar_documentos_titulacion.html', context)

@login_required
def subir_documento_personal(request, alumno_id=None):
    """Vista específica para subir documentos personales"""
    is_student = hasattr(request.user, 'alumno')
    alumno_logueado = request.user.alumno if is_student else None
    
    if request.method == 'POST':
        try:
            # 1. Determinar el usuario objetivo
            if request.user.is_superuser:
                # Si es admin, usar el alumno_id del parámetro o del formulario
                if alumno_id:
                    # Si viene del detalle del alumno, usar ese ID
                    alumno_objetivo = get_object_or_404(Alumno, id=alumno_id)
                    usuario_objetivo = alumno_objetivo.usuario
                else:
                    # Si no viene del detalle, pedir selección en el formulario
                    alumno_id_form = request.POST.get('alumno')
                    if not alumno_id_form:
                        messages.error(request, "Como administrador, debe seleccionar un alumno para asignarle el documento.")
                        raise ValueError("Alumno no especificado por el administrador.")
                    
                    alumno_objetivo = get_object_or_404(Alumno, id=alumno_id_form)
                    usuario_objetivo = alumno_objetivo.usuario
            else:
                # Si no es admin, el objetivo es el propio usuario logueado
                usuario_objetivo = request.user

            # 2. Obtener la categoría del documento personal
            categoria_id = request.POST.get('categoria')
            if not categoria_id:
                messages.error(request, 'Debe seleccionar una categoría de documento personal.')
                return redirect('subir_documento_personal')
            
            categoria = get_object_or_404(CategoriaDocumento, id=categoria_id, tipo='personal', borrado=1)

            # 3. Crear el documento personal
            DocumentoPersonal.objects.create(
                usuario=usuario_objetivo,
                categoria=categoria,
                nombre_documento=request.POST.get('nombre_documento'),
                descripcion=request.POST.get('descripcion', ''),
                archivo=request.FILES.get('archivo'),
                fecha_vencimiento=request.POST.get('fecha_vencimiento') or None,
            )
            
            messages.success(request, f'Documento personal subido exitosamente para {usuario_objetivo.username}.')
            
            # 4. Redirigir según el tipo de usuario
            if hasattr(request.user, 'alumno'):
                return redirect('detalle_alumno', alumno_id=request.user.alumno.id)
            else:
                return redirect('listar_documentos')

        except Exception as e:
            messages.error(request, f'Error al subir documento: {str(e)}')

    # Obtener categorías de documentos personales
    categorias = CategoriaDocumento.objects.filter(tipo='personal', borrado=1)
    
    # Si es admin, obtener lista de alumnos para el dropdown
    alumnos = []
    if request.user.is_superuser:
        alumnos = Alumno.objects.filter(borrado=1).select_related('usuario')

    # Obtener alumno preseleccionado si viene del detalle
    alumno_preseleccionado = None
    if alumno_id:
        try:
            alumno_preseleccionado = Alumno.objects.get(id=alumno_id, borrado=1)
        except Alumno.DoesNotExist:
            pass

    context = {
        'categorias': categorias,
        'alumnos': alumnos,
        'es_admin': request.user.is_superuser,
        'alumno_preseleccionado': alumno_preseleccionado,
    }
    return render(request, 'documentos/subir_documento_personal.html', context)

@login_required
def subir_documento_academico(request, alumno_id=None):
    """Vista específica para subir documentos académicos"""
    is_student = hasattr(request.user, 'alumno')
    alumno_logueado = request.user.alumno if is_student else None
    
    if request.method == 'POST':
        try:
            # 1. Determinar el usuario objetivo
            if request.user.is_superuser:
                # Si es admin, usar el alumno_id del parámetro o del formulario
                if alumno_id:
                    # Si viene del detalle del alumno, usar ese ID
                    alumno_objetivo = get_object_or_404(Alumno, id=alumno_id)
                else:
                    # Si no viene del detalle, pedir selección en el formulario
                    alumno_id_form = request.POST.get('alumno')
                    if not alumno_id_form:
                        messages.error(request, "Como administrador, debe seleccionar un alumno para asignarle el documento.")
                        raise ValueError("Alumno no especificado por el administrador.")
                    
                    alumno_objetivo = get_object_or_404(Alumno, id=alumno_id_form)
            else:
                # Si no es admin, el objetivo es el propio usuario logueado
                if not alumno_logueado:
                    messages.error(request, "Se requiere un perfil de alumno para subir documentos académicos. Contacte al administrador para crear su perfil de alumno.")
                    if alumno_id:
                        return redirect('subir_documento_academico_alumno', alumno_id=alumno_id)
                    else:
                        return redirect('subir_documento_academico')
                alumno_objetivo = alumno_logueado

            # 2. Obtener el tipo de documento académico
            tipo_documento = request.POST.get('tipo_documento')
            if not tipo_documento:
                messages.error(request, 'Debe seleccionar un tipo de documento académico.')
                return redirect('subir_documento_academico')

            # 3. Crear el documento académico
            DocumentoAcademico.objects.create(
                alumno=alumno_objetivo,
                tipo_documento=tipo_documento,
                titulo=request.POST.get('titulo'),
                descripcion=request.POST.get('descripcion', ''),
                archivo=request.FILES.get('archivo'),
                periodo_academico=request.POST.get('periodo_academico', ''),
            )
            
            messages.success(request, f'Documento académico subido exitosamente para {alumno_objetivo.nombre_completo}.')
            
            # 4. Redirigir según el tipo de usuario
            if hasattr(request.user, 'alumno'):
                return redirect('detalle_alumno', alumno_id=request.user.alumno.id)
            else:
                # Si viene del detalle de un alumno, regresar al detalle
                if alumno_id:
                    return redirect('detalle_alumno', alumno_id=alumno_id)
                else:
                    return redirect('listar_documentos_academicos')

        except Exception as e:
            messages.error(request, f'Error al subir documento: {str(e)}')

    # Si es admin, obtener lista de alumnos para el dropdown
    alumnos = []
    if request.user.is_superuser:
        alumnos = Alumno.objects.filter(borrado=1).select_related('usuario')

    # Obtener alumno preseleccionado si viene del detalle
    alumno_preseleccionado = None
    if alumno_id:
        try:
            alumno_preseleccionado = Alumno.objects.get(id=alumno_id, borrado=1)
        except Alumno.DoesNotExist:
            pass

    context = {
        'alumnos': alumnos,
        'es_admin': request.user.is_superuser,
        'alumno_preseleccionado': alumno_preseleccionado,
    }
    return render(request, 'documentos/subir_documento_academico.html', context)

@login_required
def subir_documento_titulacion(request, alumno_id=None):
    """Vista específica para subir documentos de titulación"""
    is_student = hasattr(request.user, 'alumno')
    alumno_logueado = request.user.alumno if is_student else None
    
    if request.method == 'POST':
        try:
            # 1. Determinar el usuario objetivo
            if request.user.is_superuser:
                # Si es admin, usar el alumno_id del parámetro o del formulario
                if alumno_id:
                    # Si viene del detalle del alumno, usar ese ID
                    alumno_objetivo = get_object_or_404(Alumno, id=alumno_id)
                else:
                    # Si no viene del detalle, pedir selección en el formulario
                    alumno_id_form = request.POST.get('alumno')
                    if not alumno_id_form:
                        messages.error(request, "Como administrador, debe seleccionar un alumno para asignarle el documento.")
                        raise ValueError("Alumno no especificado por el administrador.")
                    
                    alumno_objetivo = get_object_or_404(Alumno, id=alumno_id_form)
            else:
                # Si no es admin, el objetivo es el propio usuario logueado
                if not alumno_logueado:
                    messages.error(request, "Se requiere un perfil de alumno para subir documentos de titulación. Contacte al administrador para crear su perfil de alumno.")
                    return redirect('subir_documento_titulacion')
                alumno_objetivo = alumno_logueado

            # 2. Obtener el tipo de documento de titulación
            tipo_documento = request.POST.get('tipo_documento')
            if not tipo_documento:
                messages.error(request, 'Debe seleccionar un tipo de documento de titulación.')
                return redirect('subir_documento_titulacion')

            # 3. Crear el documento de titulación
            DocumentoAcademico.objects.create(
                alumno=alumno_objetivo,
                tipo_documento=tipo_documento,
                titulo=request.POST.get('titulo'),
                descripcion=request.POST.get('descripcion', ''),
                archivo=request.FILES.get('archivo'),
                periodo_academico=request.POST.get('periodo_academico', ''),
            )
            
            messages.success(request, f'Documento de titulación subido exitosamente para {alumno_objetivo.nombre_completo}.')
            
            # 4. Redirigir según el tipo de usuario
            if hasattr(request.user, 'alumno'):
                return redirect('detalle_alumno', alumno_id=request.user.alumno.id)
            else:
                return redirect('listar_documentos_titulacion')

        except Exception as e:
            messages.error(request, f'Error al subir documento: {str(e)}')

    # Si es admin, obtener lista de alumnos para el dropdown
    alumnos = []
    if request.user.is_superuser:
        alumnos = Alumno.objects.filter(borrado=1).select_related('usuario')

    # Obtener alumno preseleccionado si viene del detalle
    alumno_preseleccionado = None
    if alumno_id:
        try:
            alumno_preseleccionado = Alumno.objects.get(id=alumno_id, borrado=1)
        except Alumno.DoesNotExist:
            pass

    context = {
        'alumnos': alumnos,
        'es_admin': request.user.is_superuser,
        'alumno_preseleccionado': alumno_preseleccionado,
    }
    return render(request, 'documentos/subir_documento_titulacion.html', context)

@login_required
def eliminar_alumno(request, alumno_id):
    """Vista para eliminar un alumno y todos sus datos asociados"""
    if not request.user.is_superuser:
        messages.error(request, 'No tienes permisos para eliminar alumnos.')
        return redirect('listar_alumnos')
    
    alumno = get_object_or_404(Alumno, id=alumno_id)
    
    if request.method == 'POST':
        try:
            # Obtener información del alumno antes de eliminar
            nombre_alumno = alumno.nombre_completo
            matricula = alumno.matricula
            
            # Eliminar datos relacionados
            # 1. Eliminar calificaciones
            Calificacion.objects.filter(alumno=alumno).delete()
            
            # 2. Eliminar documentos académicos
            DocumentoAcademico.objects.filter(alumno=alumno).delete()
            
            # 3. Eliminar documentos personales (si el usuario tiene perfil de alumno)
            if hasattr(alumno, 'usuario') and alumno.usuario:
                DocumentoPersonal.objects.filter(usuario=alumno.usuario).delete()
            
            # 4. Eliminar el perfil de alumno
            alumno.delete()
            
            # 5. Si el usuario solo tenía perfil de alumno, eliminar también el usuario
            if hasattr(alumno, 'usuario') and alumno.usuario:
                # Verificar si el usuario tiene otros perfiles o es superusuario
                if not alumno.usuario.is_superuser and not hasattr(alumno.usuario, 'profesor'):
                    alumno.usuario.delete()
            
            messages.success(request, f'Alumno {nombre_alumno} ({matricula}) eliminado exitosamente junto con todos sus datos asociados.')
            return redirect('listar_alumnos')
            
        except Exception as e:
            messages.error(request, f'Error al eliminar alumno: {str(e)}')
            return redirect('listar_alumnos')
    
    # Si no es POST, mostrar confirmación
    context = {
        'alumno': alumno,
    }
    return render(request, 'cardex/eliminar_alumno.html', context)


@login_required
def ver_perfil_admin(request):
    """Vista para que un administrador vea y edite su propio perfil."""
    if not request.user.is_superuser:
        messages.error(request, "Acceso denegado.")
        return redirect('homeP')
    
    usuario = request.user
    tb_usuario, created = tb_usaurios.objects.get_or_create(id_user_fk=usuario)
    
    if request.method == 'POST':
        # Editar información del perfil
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        whatsapp = request.POST.get('whatsapp', '').strip()
        direccion = request.POST.get('direccion', '').strip()
        fecha_nacimiento = request.POST.get('fecha_nacimiento', '').strip()
        
        try:
            # Actualizar información del usuario
            usuario.email = email
            usuario.first_name = first_name
            usuario.last_name = last_name
            usuario.save()
            
            # Actualizar información adicional
            tb_usuario.telefono = telefono if telefono else None
            tb_usuario.whatsapp = whatsapp if whatsapp else None
            tb_usuario.direccion = direccion if direccion else None
            tb_usuario.fecha_nacimiento = fecha_nacimiento if fecha_nacimiento else None
            tb_usuario.save()
            
            messages.success(request, "Tu perfil ha sido actualizado exitosamente.")
            return redirect('ver_perfil_admin')
        except Exception as e:
            messages.error(request, f"Error al actualizar el perfil: {str(e)}")
    
    context = {
        'usuario': usuario,
        'tb_usuario': tb_usuario,
    }
    return render(request, 'admin/ver_perfil_admin.html', context)


# =============================================================================
# VISTAS PARA ASPIRANTES (Ingreso sin cuenta registrada)
# =============================================================================

def ingreso_aspirante(request):
    """Vista para que los aspirantes accedan sin necesidad de tener una cuenta registrada"""
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        apellidos = request.POST.get('apellidos', '').strip()
        email = request.POST.get('email', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        curp = request.POST.get('curp', '').strip()
        
        try:
            # Validar que el email no exista ni en usuarios ni en aspirantes
            if User.objects.filter(email=email).exists():
                messages.error(request, "Este correo electrónico ya está registrado. Por favor, inicia sesión.")
                return redirect('signin')
            
            if Aspirante.objects.filter(email=email, borrado=1).exists():
                messages.error(request, "Este correo electrónico ya ha sido registrado como aspirante.")
                return redirect('ingreso_aspirante')
            
            # Crear nuevo aspirante
            aspirante = Aspirante.objects.create(
                nombre=nombre,
                apellidos=apellidos,
                email=email,
                telefono=telefono if telefono else None,
                curp=curp if curp else None,
                borrado=1
            )
            
            # Guardar aspirante en sesión para usarlo en subir_documento_aspirante
            request.session['aspirante_id'] = aspirante.id
            request.session['aspirante_nombre'] = aspirante.nombre_completo
            
            messages.success(request, f"¡Bienvenido {aspirante.nombre_completo}! Ahora puedes subir tus documentos.")
            return redirect('subir_documento_aspirante')
            
        except Exception as e:
            messages.error(request, f"Error al procesar tu solicitud: {str(e)}")
            return redirect('ingreso_aspirante')
    
    return render(request, 'aspirante/ingreso_aspirante.html')


def subir_documento_aspirante(request):
    """Vista para que los aspirantes suban documentos sin estar registrados"""
    # Verificar que el aspirante esté en sesión
    aspirante_id = request.session.get('aspirante_id')
    if not aspirante_id:
        messages.error(request, "Debes acceder como aspirante primero.")
        return redirect('ingreso_aspirante')
    
    try:
        aspirante = Aspirante.objects.get(id=aspirante_id, borrado=1)
    except Aspirante.DoesNotExist:
        messages.error(request, "Aspirante no encontrado.")
        request.session.pop('aspirante_id', None)
        request.session.pop('aspirante_nombre', None)
        return redirect('ingreso_aspirante')
    
    if request.method == 'POST':
        try:
            categoria_id = request.POST.get('categoria')
            nombre_documento = request.POST.get('nombre_documento', '').strip()
            descripcion = request.POST.get('descripcion', '').strip()
            archivo = request.FILES.get('archivo')
            
            if not all([categoria_id, nombre_documento, archivo]):
                messages.error(request, "Por favor, completa todos los campos requeridos.")
                return redirect('subir_documento_aspirante')
            
            categoria = get_object_or_404(CategoriaDocumento, id=categoria_id, borrado=1)
            
            # Crear documento para el aspirante
            DocumentoPersonal.objects.create(
                aspirante=aspirante,
                categoria=categoria,
                nombre_documento=nombre_documento,
                descripcion=descripcion,
                archivo=archivo,
                estado='pendiente',
                borrado=1
            )
            
            messages.success(request, f"¡Documento '{nombre_documento}' subido exitosamente! Será revisado pronto.")
            return redirect('documentos_aspirante')
            
        except Exception as e:
            messages.error(request, f"Error al subir documento: {str(e)}")
            return redirect('subir_documento_aspirante')
    
    # Obtener categorías de documentos personales y académicos
    categorias = CategoriaDocumento.objects.filter(tipo__in=['personal', 'academico'], borrado=1).order_by('tipo', 'nombre')
    
    context = {
        'aspirante': aspirante,
        'categorias': categorias,
    }
    return render(request, 'aspirante/subir_documento_aspirante.html', context)


def documentos_aspirante(request):
    """Vista para que los aspirantes vean sus documentos subidos"""
    aspirante_id = request.session.get('aspirante_id')
    if not aspirante_id:
        messages.error(request, "Debes acceder como aspirante primero.")
        return redirect('ingreso_aspirante')
    
    try:
        aspirante = Aspirante.objects.get(id=aspirante_id, borrado=1)
    except Aspirante.DoesNotExist:
        messages.error(request, "Aspirante no encontrado.")
        request.session.pop('aspirante_id', None)
        request.session.pop('aspirante_nombre', None)
        return redirect('ingreso_aspirante')
    
    documentos = DocumentoPersonal.objects.filter(aspirante=aspirante, borrado=1)
    
    # Contar documentos por estado
    pendientes = documentos.filter(estado='pendiente').count()
    aprobados = documentos.filter(estado='aprobado').count()
    rechazados = documentos.filter(estado='rechazado').count()
    
    context = {
        'aspirante': aspirante,
        'documentos': documentos,
        'pendientes': pendientes,
        'aprobados': aprobados,
        'rechazados': rechazados,
    }
    return render(request, 'aspirante/documentos_aspirante.html', context)


def cerrar_sesion_aspirante(request):
    """Vista para que los aspirantes cierren sesión"""
    request.session.pop('aspirante_id', None)
    request.session.pop('aspirante_nombre', None)
    messages.success(request, "Sesión de aspirante cerrada. ¡Hasta luego!")
    return redirect('signin')


# =============================================================================
# VISTAS PARA GESTIÓN DE ASPIRANTES (Solo Administrador)
# =============================================================================

@login_required
def gestionar_aspirantes(request):
    """Vista para listar y gestionar aspirantes (solo admin y usuarios autorizados)"""
    # Verificar que es admin o tiene permiso
    if not request.user.is_superuser:
        # Aquí puedes agregar lógica para verificar si el usuario tiene permiso
        # Por ahora, solo acceso a admin
        messages.error(request, "No tienes permiso para acceder a esta sección.")
        return redirect('homeP')
    
    # Filtros
    estado = request.GET.get('estado', '')
    busqueda = request.GET.get('busqueda', '')
    
    aspirantes = Aspirante.objects.filter(borrado=1)
    
    if estado:
        aspirantes = aspirantes.filter(estado=estado)
    
    if busqueda:
        aspirantes = aspirantes.filter(
            models.Q(nombre__icontains=busqueda) |
            models.Q(apellidos__icontains=busqueda) |
            models.Q(email__icontains=busqueda) |
            models.Q(curp__icontains=busqueda)
        )
    
    # Contar por estado
    total = Aspirante.objects.filter(borrado=1).count()
    nuevos = Aspirante.objects.filter(estado='nuevo', borrado=1).count()
    en_revision = Aspirante.objects.filter(estado='en_revision', borrado=1).count()
    aceptados = Aspirante.objects.filter(estado='aceptado', borrado=1).count()
    rechazados = Aspirante.objects.filter(estado='rechazado', borrado=1).count()
    
    context = {
        'aspirantes': aspirantes.order_by('-fecha_creacion'),
        'total': total,
        'nuevos': nuevos,
        'en_revision': en_revision,
        'aceptados': aceptados,
        'rechazados': rechazados,
        'estado_filtro': estado,
        'busqueda': busqueda,
    }
    return render(request, 'admin/gestionar_aspirantes.html', context)


@login_required
def detalle_aspirante(request, aspirante_id):
    """Vista para ver detalles de un aspirante y sus documentos"""
    if not request.user.is_superuser:
        messages.error(request, "No tienes permiso para acceder a esta sección.")
        return redirect('homeP')
    
    aspirante = get_object_or_404(Aspirante, id=aspirante_id, borrado=1)
    documentos = DocumentoPersonal.objects.filter(aspirante=aspirante, borrado=1)
    
    if request.method == 'POST':
        try:
            accion = request.POST.get('accion')
            estado_nuevo = request.POST.get('estado')
            observaciones = request.POST.get('observaciones', '').strip()
            
            if accion == 'actualizar_estado':
                # Si el nuevo estado es "aceptado", crear alumno automáticamente
                if estado_nuevo == 'aceptado':
                    # Verificar si ya existe un usuario con este email
                    usuario_existente = User.objects.filter(username=aspirante.email).first()
                    
                    if usuario_existente:
                        messages.warning(request, f"El usuario con correo {aspirante.email} ya existe. Se vinculará al alumno existente.")
                        # Actualizar estado del aspirante
                        aspirante.estado = estado_nuevo
                        aspirante.observaciones = observaciones
                        aspirante.usuario_asignado = request.user
                        aspirante.fecha_ultima_revision = timezone.now()
                        aspirante.save()
                    else:
                        try:
                            # Crear usuario con email como username
                            usuario = User.objects.create_user(
                                username=aspirante.email,
                                email=aspirante.email,
                                password='12345678',
                                first_name=aspirante.nombre,
                                last_name=aspirante.apellidos
                            )
                            
                            # Generar matrícula única
                            from datetime import datetime
                            import random
                            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                            random_num = random.randint(1000, 9999)
                            matricula = f"ALU{timestamp}{random_num}"
                            
                            # Obtener fecha de nacimiento del CURP si está disponible
                            fecha_nacimiento = None
                            if aspirante.curp and len(aspirante.curp) >= 6:
                                try:
                                    # El CURP contiene fecha de nacimiento en posición 4-9 (YYMMDD)
                                    fecha_str = aspirante.curp[4:10]
                                    año = int(fecha_str[0:2])
                                    mes = int(fecha_str[2:4])
                                    día = int(fecha_str[4:6])
                                    # Ajustar año (si es mayor a 50, es 19XX, sino es 20XX)
                                    if año > 50:
                                        año = 1900 + año
                                    else:
                                        año = 2000 + año
                                    fecha_nacimiento = timezone.datetime(año, mes, día).date()
                                except:
                                    fecha_nacimiento = timezone.datetime(2000, 1, 1).date()
                            else:
                                fecha_nacimiento = timezone.datetime(2000, 1, 1).date()
                            
                            # Separar apellidos
                            apellidos_split = aspirante.apellidos.split()
                            apellido_paterno = apellidos_split[0] if len(apellidos_split) > 0 else aspirante.apellidos
                            apellido_materno = apellidos_split[1] if len(apellidos_split) > 1 else ''
                            
                            # Crear alumno con los datos básicos del aspirante
                            # Carrera se asignará posteriormente
                            alumno = Alumno.objects.create(
                                usuario=usuario,
                                matricula=matricula,
                                nombre=aspirante.nombre,
                                apellido_paterno=apellido_paterno,
                                apellido_materno=apellido_materno,
                                fecha_nacimiento=fecha_nacimiento,
                                email_institucional=aspirante.email,
                                telefono=aspirante.telefono if aspirante.telefono else '',
                                curp=aspirante.curp if aspirante.curp else None,
                                carrera=None,  # Se asignará posteriormente
                                estado='activo',
                                semestre_actual=1,
                                borrado=1
                            )
                            
                            # Actualizar estado del aspirante
                            aspirante.estado = estado_nuevo
                            aspirante.observaciones = observaciones
                            aspirante.usuario_asignado = request.user
                            aspirante.fecha_ultima_revision = timezone.now()
                            aspirante.save()
                            
                            messages.success(request, f"✓ Aspirante {aspirante.nombre_completo} ACEPTADO y convertido a alumno.")
                            messages.info(request, f"Usuario: {aspirante.email} | Contraseña: 12345678 | Matrícula: {matricula}")
                        
                        except Exception as e:
                            messages.error(request, f"Error al crear alumno: {str(e)}")
                            return redirect('detalle_aspirante', aspirante_id=aspirante.id)
                    
                    return redirect('detalle_aspirante', aspirante_id=aspirante.id)
                else:
                    # Para otros estados
                    # Actualizar estado del aspirante
                    aspirante.estado = estado_nuevo
                    aspirante.observaciones = observaciones
                    aspirante.usuario_asignado = request.user
                    aspirante.fecha_ultima_revision = timezone.now()
                    aspirante.save()
                    
                    messages.success(request, f"Aspirante {aspirante.nombre_completo} actualizado a: {estado_nuevo}")
                    return redirect('detalle_aspirante', aspirante_id=aspirante.id)
            
        except Exception as e:
            messages.error(request, f"Error al actualizar: {str(e)}")
    
    context = {
        'aspirante': aspirante,
        'documentos': documentos,
    }
    return render(request, 'admin/detalle_aspirante.html', context)


@login_required
def editar_aspirante(request, aspirante_id):
    """Vista para editar información del aspirante"""
    if not request.user.is_superuser:
        messages.error(request, "No tienes permiso para acceder a esta sección.")
        return redirect('homeP')
    
    aspirante = get_object_or_404(Aspirante, id=aspirante_id, borrado=1)
    
    if request.method == 'POST':
        try:
            aspirante.nombre = request.POST.get('nombre', '').strip()
            aspirante.apellidos = request.POST.get('apellidos', '').strip()
            aspirante.telefono = request.POST.get('telefono', '').strip() or None
            aspirante.curp = request.POST.get('curp', '').strip() or None
            aspirante.save()
            
            messages.success(request, f"Aspirante {aspirante.nombre_completo} actualizado exitosamente.")
            return redirect('detalle_aspirante', aspirante_id=aspirante.id)
        
        except Exception as e:
            messages.error(request, f"Error al actualizar: {str(e)}")
    
    context = {
        'aspirante': aspirante,
    }
    return render(request, 'admin/editar_aspirante.html', context)


@login_required
def eliminar_aspirante(request, aspirante_id):
    """Vista para eliminar (soft delete) un aspirante"""
    if not request.user.is_superuser:
        messages.error(request, "No tienes permiso para acceder a esta sección.")
        return redirect('homeP')
    
    aspirante = get_object_or_404(Aspirante, id=aspirante_id, borrado=1)
    
    if request.method == 'POST':
        try:
            aspirante.borrado = 0
            aspirante.save()
            
            messages.success(request, f"Aspirante {aspirante.nombre_completo} eliminado exitosamente.")
            return redirect('gestionar_aspirantes')
        
        except Exception as e:
            messages.error(request, f"Error al eliminar: {str(e)}")
    
    context = {
        'aspirante': aspirante,
    }
    return render(request, 'admin/eliminar_aspirante.html', context)


@login_required
def asignar_revisores_aspirantes(request):
    """Vista para asignar permisos de revisión de aspirantes a otros usuarios"""
    if not request.user.is_superuser:
        messages.error(request, "No tienes permiso para acceder a esta sección.")
        return redirect('homeP')
    
    # Obtener usuarios que tienen permiso de revisar aspirantes
    usuarios_con_permiso = User.objects.filter(
        tb_usaurios__isnull=False
    ).exclude(id=request.user.id)
    
    # Marcamos quiénes ya tienen permiso (usuarios que han revisado aspirantes)
    usuarios_revisores = set(
        Aspirante.objects.filter(
            usuario_asignado__isnull=False,
            borrado=1
        ).values_list('usuario_asignado_id', flat=True).distinct()
    )
    
    if request.method == 'POST':
        try:
            usuario_id = request.POST.get('usuario_id')
            accion = request.POST.get('accion')  # 'asignar' o 'revocar'
            
            usuario = get_object_or_404(User, id=usuario_id)
            
            if accion == 'asignar':
                # Simplemente guardamos un registro de que este usuario puede revisar
                # En un sistema más complejo, usarías un modelo Permission
                messages.success(request, f"Permiso de revisión otorgado a {usuario.get_full_name() or usuario.username}")
            elif accion == 'revocar':
                # Removemos todos los aspirantes asignados
                Aspirante.objects.filter(usuario_asignado=usuario, borrado=1).update(usuario_asignado=None)
                messages.success(request, f"Permiso de revisión revocado a {usuario.get_full_name() or usuario.username}")
            
            return redirect('asignar_revisores_aspirantes')
        
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
    
    context = {
        'usuarios': usuarios_con_permiso,
        'usuarios_revisores': usuarios_revisores,
    }
    return render(request, 'admin/asignar_revisores_aspirantes.html', context)


@login_required
def aprobar_documento_aspirante(request, documento_id):
    """Vista para aprobar un documento de aspirante"""
    if not request.user.is_superuser:
        messages.error(request, "No tienes permisos para realizar esta acción.")
        return redirect('homeP')
    
    documento = get_object_or_404(DocumentoPersonal, id=documento_id, borrado=1)
    
    if request.method == 'POST':
        try:
            documento.estado = 'aprobado'
            documento.observaciones = ''
            documento.save()
            messages.success(request, f'Documento "{documento.nombre_documento}" aprobado exitosamente.')
            return redirect('detalle_aspirante', aspirante_id=documento.aspirante.id)
        except Exception as e:
            messages.error(request, f'Error al aprobar documento: {str(e)}')
    
    return redirect('detalle_aspirante', aspirante_id=documento.aspirante.id)


@login_required
def rechazar_documento_aspirante(request, documento_id):
    """Vista para rechazar un documento de aspirante"""
    if not request.user.is_superuser:
        messages.error(request, "No tienes permisos para realizar esta acción.")
        return redirect('homeP')
    
    documento = get_object_or_404(DocumentoPersonal, id=documento_id, borrado=1)
    
    if request.method == 'POST':
        try:
            observaciones = request.POST.get('observaciones', '').strip()
            if not observaciones:
                messages.error(request, 'Debes proporcionar un motivo para rechazar el documento.')
                return redirect('detalle_aspirante', aspirante_id=documento.aspirante.id)
            
            documento.estado = 'rechazado'
            documento.observaciones = observaciones
            documento.save()
            messages.error(request, f'Documento "{documento.nombre_documento}" rechazado.')
            return redirect('detalle_aspirante', aspirante_id=documento.aspirante.id)
        except Exception as e:
            messages.error(request, f'Error al rechazar documento: {str(e)}')
    
    return redirect('detalle_aspirante', aspirante_id=documento.aspirante.id)
