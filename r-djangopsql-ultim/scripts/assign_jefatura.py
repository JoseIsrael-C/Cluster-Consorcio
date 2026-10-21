#!/usr/bin/env python
import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blockchainpd.settings')
django.setup()

from django.contrib.auth.models import User
from management.models import ct_perfil, tb_usaurios

if len(sys.argv) < 2:
    print('Usage: python assign_jefatura.py <username_or_email>')
    sys.exit(1)

identifier = sys.argv[1]

try:
    # buscar por username, luego por email
    user = None
    try:
        user = User.objects.get(username=identifier)
    except User.DoesNotExist:
        try:
            user = User.objects.get(email=identifier)
        except User.DoesNotExist:
            print('Usuario no encontrado con username o email:', identifier)
            sys.exit(1)

    perfil, created = ct_perfil.objects.get_or_create(nombre='Jefatura de División', defaults={'borrado': 1})
    tb_usuario, created_tb = tb_usaurios.objects.get_or_create(id_user_fk=user)
    tb_usuario.perfil_fk = perfil
    tb_usuario.save()

    print(f'Perfil Jefatura de División asignado a {user.username} ({user.email})')

except Exception as e:
    print('Error:', e)
    sys.exit(1)
