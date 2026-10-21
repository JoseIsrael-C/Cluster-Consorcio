from .models import Alumno
from .views import obtener_menu_dinamico

def student_context(request):
    """
    Añade al contexto de la plantilla información sobre si el usuario es un alumno.
    """
    context = {
        'is_student': False,
        'alumno_instance': None,
        'is_jefatura': False,
        'is_control_escolar': False,
        'is_profesor': False,
        'menu_dinamico': obtener_menu_dinamico(request.user),
    }
    
    if request.user.is_authenticated:
        # 1. Verificar roles especiales (Jefatura o Control Escolar)
        es_jefatura = False
        es_control_escolar = False
        es_profesor = False
        
        try:
            if hasattr(request.user, 'perfil_usuario') and request.user.perfil_usuario.perfil_fk:
                nombre = request.user.perfil_usuario.perfil_fk.nombre.strip().lower()
                
                if 'jefatura' in nombre:
                    es_jefatura = True
                    context['is_jefatura'] = True
                # Verificación más flexible: busca 'control' Y 'escolar' aunque haya palabras en medio
                elif ('control' in nombre and 'escolar' in nombre) or 'control_escolar' in nombre:
                    es_control_escolar = True
                    context['is_control_escolar'] = True
                elif 'profesor' in nombre or 'maestro' in nombre or 'docente' in nombre:
                    es_profesor = True
                    context['is_profesor'] = True
        except Exception as e:
            print(f"--- ERROR en context_processor: {e} ---")

        # 2. Verificar si es alumno (Solo si NO es superusuario y NO tiene rol especial)
        if not request.user.is_superuser and not es_jefatura and not es_control_escolar and not es_profesor:
            try:
                # hasattr es más seguro que un try-except directo en el objeto user
                if hasattr(request.user, 'alumno'):
                    context['is_student'] = True
                    context['alumno_instance'] = request.user.alumno
            except Alumno.DoesNotExist:
                pass  # El usuario no tiene un perfil de alumno asociado
    return context