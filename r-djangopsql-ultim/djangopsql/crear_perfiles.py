#!/usr/bin/env python
import os
import sys
import django

# Configurar el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blockchainpd.settings')
django.setup()

# Importar el modelo de Perfil
from management.models import ct_perfil

def crear_perfiles_iniciales():
    """
    Crea los perfiles/roles iniciales del sistema si no existen.
    """
    
    # --- ¡MODIFICA ESTA LISTA CON LOS PERFILES QUE NECESITES! ---
    perfiles_a_crear = [
        'Administrador',
        'Secretaría Académica',
        'Jefatura de División',
        'Control Escolar',
        'Profesor',
        'Aspirante'
    ]
    
    print("Iniciando la creación de perfiles iniciales...")
    
    for nombre_perfil in perfiles_a_crear:
        # get_or_create evita crear duplicados si el script se ejecuta varias veces.
        perfil, created = ct_perfil.objects.get_or_create(
            nombre=nombre_perfil,
            defaults={'borrado': 1}  # Asumiendo que 1 es 'activo'
        )
        
        if created:
            print(f" Perfil '{nombre_perfil}' creado exitosamente.")
        else:
            print(f" El perfil '{nombre_perfil}' ya existía.")
            
    print(f"\nProceso finalizado. Total de perfiles activos: {ct_perfil.objects.filter(borrado=1).count()}")

if __name__ == '__main__':
    crear_perfiles_iniciales()
