# Sistema r-djangopsql-ultim

## 📋 Descripción del Proyecto

Sistema integral de gestión desarrollado en Django que incluye:
- **Sistema de Login y Autenticación**
- **Administración de Módulos y Roles**
- **Gestión de Documentos Personales**
- **Sistema de Cardex (Control de Inventario)**

## 🚀 Funcionalidades Implementadas

### 1. Sistema de Autenticación
- ✅ Login/Logout de usuarios
- ✅ Registro de nuevos usuarios
- ✅ Control de acceso con decoradores `@login_required`
- ✅ Redirecciones automáticas de seguridad
- ✅ Gestión de perfiles de usuario

### 2. Administración de Módulos y Roles
- ✅ Gestión de perfiles (roles) de usuario
- ✅ Administración de módulos del sistema
- ✅ Gestión de submódulos
- ✅ Control de puestos de trabajo
- ✅ Relación many-to-many entre perfiles y módulos

### 3. Sistema de Documentos Personales
- ✅ Subida de documentos (PDF, DOC, DOCX, JPG, PNG)
- ✅ Categorización de documentos
- ✅ Control de fechas de vencimiento
- ✅ Estados de documentos (pendiente, aprobado, rechazado)
- ✅ Descarga de archivos
- ✅ Edición y eliminación de documentos
- ✅ Gestión de categorías de documentos

### 4. Sistema de Cardex (Inventario)
- ✅ Dashboard con métricas de inventario
- ✅ Gestión de productos con códigos únicos
- ✅ Categorización de productos
- ✅ Control de stock (mínimo, máximo, actual)
- ✅ Registro de movimientos (entrada, salida, ajuste)
- ✅ Historial completo de movimientos
- ✅ Alertas de bajo stock
- ✅ Cálculo automático de totales

## 🗂️ Estructura de Modelos

### Modelos de Usuario y Perfiles
- `ct_perfil`: Perfiles/roles de usuario
- `tb_usaurios`: Información extendida de usuarios
- `ct_puestos`: Catálogo de puestos de trabajo

### Modelos de Módulos
- `ct_modulos`: Módulos del sistema
- `ct_submodulos`: Submódulos
- `mainmenu` y `MenuList`: Sistema de menús dinámicos

### Modelos de Documentos
- `CategoriaDocumento`: Categorías para clasificar documentos
- `DocumentoPersonal`: Documentos de usuarios con metadatos

### Modelos de Cardex
- `CategoriaProducto`: Categorías de productos
- `Producto`: Productos del inventario
- `MovimientoCardex`: Movimientos de inventario
- `Inventario`: Estado actual del inventario

### Auditoría
- `tb_bitacora`: Registro de acciones del sistema
- `simple_history`: Auditoría automática de cambios

## 🌐 URLs Principales

### Autenticación
- `/` - Página principal
- `/signin/` - Iniciar sesión
- `/signup/` - Registro de usuario
- `/logout/` - Cerrar sesión

### Administración
- `/management/perfil/` - Gestión de perfiles y catálogos
- `/management/admin/categorias-documentos/` - Gestión de categorías de documentos
- `/management/admin/categorias-productos/` - Gestión de categorías de productos

### Documentos Personales
- `/management/documentos/` - Lista de documentos
- `/management/documentos/subir/` - Subir documento
- `/management/documentos/editar/<id>/` - Editar documento

### Sistema de Cardex
- `/management/cardex/` - Dashboard del cardex
- `/management/cardex/productos/` - Lista de productos
- `/management/cardex/productos/crear/` - Crear producto
- `/management/cardex/movimientos/` - Registrar movimiento
- `/management/cardex/historial/` - Historial de movimientos

### Certificados (Blockchain)
- `/management/certificados/` - Sistema de certificados

## 🛠️ Tecnologías Utilizadas

- **Backend**: Django 5.1.1
- **Base de Datos**: PostgreSQL
- **Frontend**: Bootstrap 5.3.3
- **Iconos**: Font Awesome 6.0.0
- **Auditoría**: django-simple-history
- **Archivos**: Sistema de archivos local con Django

## 📁 Estructura de Archivos

```
djangopsql/
├── blockchainpd/           # Configuración del proyecto
│   ├── settings.py         # Configuraciones
│   ├── urls.py            # URLs principales
│   └── ...
├── management/            # Aplicación principal
│   ├── models.py          # Modelos de datos
│   ├── views.py           # Vistas/controladores
│   ├── urls.py            # URLs de la aplicación
│   ├── forms.py           # Formularios
│   ├── templates/         # Templates HTML
│   │   ├── documentos/    # Templates de documentos
│   │   ├── cardex/        # Templates de cardex
│   │   ├── admin/         # Templates de administración
│   │   └── ...
│   ├── migrations/        # Migraciones de BD
│   └── static/           # Archivos estáticos
├── media/                # Archivos subidos
├── manage.py             # Comando de Django
└── README.md            # Este archivo
```

## 🚀 Instalación y Configuración

### Prerrequisitos
- Python 3.8+
- PostgreSQL
- pip (gestor de paquetes de Python)

### Pasos de Instalación

1. **Clonar el repositorio**
   ```bash
   git clone <repository-url>
   cd r-djangopsql-ultim/djangopsql
   ```

2. **Crear entorno virtual**
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```

3. **Instalar dependencias**
   ```bash
   pip install django psycopg2-binary django-simple-history
   ```

4. **Configurar base de datos**
   - Crear base de datos PostgreSQL llamada `blockchange`
   - Usuario: `postgres`
   - Contraseña: `Papas2025`
   - Host: `localhost`
   - Puerto: `5432`

5. **Aplicar migraciones**
   ```bash
   python manage.py migrate
   ```

6. **Crear superusuario**
   ```bash
   python manage.py createsuperuser
   ```

7. **Ejecutar servidor**
   ```bash
   python manage.py runserver
   ```

## 🔧 Configuración Adicional

### Archivos Multimedia
El sistema está configurado para manejar archivos en la carpeta `media/`. Asegúrese de que esta carpeta tenga permisos de escritura.

### Configuraciones de Seguridad
- `DEBUG = True` (solo para desarrollo)
- `SECRET_KEY` debe cambiarse en producción
- Configurar `ALLOWED_HOSTS` para producción

## 📊 Características Destacadas

### Sistema de Documentos
- **Validación de archivos**: Solo permite formatos específicos
- **Control de tamaño**: Máximo 10MB por archivo
- **Estados de aprobación**: Workflow de aprobación de documentos
- **Fechas de vencimiento**: Alertas automáticas de vencimiento

### Sistema de Cardex
- **Control de stock inteligente**: Alertas automáticas de bajo stock
- **Validaciones de movimientos**: Previene salidas con stock insuficiente
- **Cálculos automáticos**: Stock y valores se actualizan automáticamente
- **Historial completo**: Auditoría completa de todos los movimientos

### Seguridad
- **Autenticación requerida**: Todas las funciones principales requieren login
- **Control de acceso**: Redirecciones automáticas para usuarios no autenticados
- **Auditoría**: Registro completo de cambios con `simple_history`

## 🎯 Próximas Mejoras

- [ ] Sistema de permisos más granular
- [ ] Reportes en PDF
- [ ] API REST
- [ ] Notificaciones por email
- [ ] Dashboard con gráficos
- [ ] Exportación de datos
- [ ] Sistema de backup automático

## 👥 Contribución

Para contribuir al proyecto:
1. Fork el repositorio
2. Crear una rama para la nueva funcionalidad
3. Realizar los cambios
4. Enviar pull request

## 📞 Soporte

Para soporte técnico o consultas sobre el sistema, contactar al equipo de desarrollo.

---

**Desarrollado con ❤️ usando Django y PostgreSQL**
