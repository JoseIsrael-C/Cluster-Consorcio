#!/usr/bin/env python
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blockchainpd.settings')
django.setup()

from management.models import CategoriaDocumento

def crear_categorias_documentos():
    """Crear las categorías de documentos necesarias si no existen"""
    
    categorias_personales = [
        'Acta de Nacimiento',
        'CURP',
        'Comprobante de Domicilio',
        'Fotografía',
        'Identificación Oficial',
        'Comprobante de Ingresos',
        'Carta de Buena Conducta',
        'Certificado Médico',
    ]
    
    categorias_admision = [
        'Certificado de Bachillerato',
        'Acta de Nacimiento',
        'CURP',
        'Comprobante de Domicilio',
        'Fotografía',
        'Identificación Oficial',
        'Carta de Motivos',
        'Carta de Recomendación',
        'Examen de Admisión',
        'Entrevista',
    ]
    
    print("Creando categorías de documentos...")
    
    # Crear categorías personales
    for nombre in categorias_personales:
        categoria, created = CategoriaDocumento.objects.get_or_create(
            nombre=nombre,
            tipo='personal',
            defaults={
                'descripcion': f'Documento personal: {nombre}',
                'borrado': 1
            }
        )
        if created:
            print(f"✓ Creada categoría personal: {nombre}")
        else:
            print(f"- Categoría personal ya existe: {nombre}")
    
    # Crear categorías de admisión
    for nombre in categorias_admision:
        categoria, created = CategoriaDocumento.objects.get_or_create(
            nombre=nombre,
            tipo='admision',
            defaults={
                'descripcion': f'Documento de admisión: {nombre}',
                'borrado': 1
            }
        )
        if created:
            print(f"✓ Creada categoría de admisión: {nombre}")
        else:
            print(f"- Categoría de admisión ya existe: {nombre}")
    
    print(f"\nTotal de categorías personales: {CategoriaDocumento.objects.filter(tipo='personal', borrado=1).count()}")
    print(f"Total de categorías de admisión: {CategoriaDocumento.objects.filter(tipo='admision', borrado=1).count()}")

if __name__ == '__main__':
    crear_categorias_documentos()

