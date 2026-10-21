from django.db import models
from django.db.models.signals import post_save
from simple_history.models import HistoricalRecords
#ocupar la tablas echas por django o por defecto
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here.
#crear los perfiles para los permisos
class ct_perfil (models.Model):
    nombre = models.CharField(blank=True,max_length=25)
    borrado= models.IntegerField(blank=True,default=1)
    modulos = models.ManyToManyField('ct_modulos', through='Permiso', blank=True, related_name='perfiles')
    
    def __str__(self):
        return self.nombre

#crear los modulos para cada perfil
class ct_modulos (models.Model):
    nombre = models.CharField(blank=True, max_length=50)
    clave = models.CharField(max_length=50, unique=True, null=True, blank=True, help_text="Clave única para identificar el módulo en el código, ej: 'alumnos', 'documentos_personales'")
    url = models.CharField(blank=True, max_length=150)
    borrado=models.IntegerField(blank=True,default=1)
    
    def __str__(self):
        return self.nombre

# Tabla intermedia para gestionar permisos granulares (CRUD) por perfil y módulo
class Permiso(models.Model):
    perfil = models.ForeignKey(ct_perfil, on_delete=models.CASCADE)
    modulo = models.ForeignKey(ct_modulos, on_delete=models.CASCADE)
    puede_leer = models.BooleanField(default=True, help_text="Permiso para ver/listar")
    puede_crear = models.BooleanField(default=False, help_text="Permiso para crear nuevos registros")
    puede_actualizar = models.BooleanField(default=False, help_text="Permiso para editar registros existentes")
    puede_eliminar = models.BooleanField(default=False, help_text="Permiso para eliminar registros")

    class Meta:
        unique_together = ('perfil', 'modulo')
        verbose_name = 'Permiso'
        verbose_name_plural = 'Permisos'

    def __str__(self):
        return f"Permisos para {self.perfil.nombre} en {self.modulo.nombre}"

#crear los sub modulos, las URLs para cada perfil
class ct_submodulos (models.Model):
    nombre = models.CharField(blank=True,max_length=25)
    url = models.CharField(blank=True, max_length=150)
    borrado=models.IntegerField(blank=True,default=1)
    id_modulo_fk=models.OneToOneField(ct_modulos, on_delete=models.CASCADE,null=True)

    def __str__(self):
        return f"{self.nombre} - {self.url}"
    
#tabla de la relacion de modulos con los perfiles 
#class tb_modulos_perfil(models.Model):
#    id_perfil=models.ForeignKey(ct_perfil, editable=True,on_delete=models.CASCADE)
#    id_modulo=models.ForeignKey(ct_modulos,editable=True,on_delete=models.CASCADE)
#    borrado = models.IntegerField(blank=True,default=1)

#catalogo de los puestos que va a ver
class ct_puestos (models.Model):
    nombre = models.CharField(blank=True, max_length=25)
    borrado= models.IntegerField(blank=True,default=1)

#tabla para guardar los usuarios
class tb_usaurios (models.Model):
    telefono= models.CharField(max_length=15, blank=True, null=True)
    whatsapp= models.CharField(max_length=15, blank=True, null=True)
    registro= models.CharField(max_length=20, blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)
    fecha_nacimiento = models.DateField(blank=True, null=True)
    borrado = models.IntegerField(blank=True,default=1)
    mostrar_menu_rapido = models.BooleanField(default=True, help_text="Permite mostrar el menú rápido al usuario")
    id_user_fk=models.OneToOneField(User,editable=True, null=True, on_delete=models.CASCADE, related_name='perfil_usuario')
    perfil_fk=models.ForeignKey(ct_perfil, on_delete=models.SET_NULL, null=True, blank=True, related_name='usuarios')

    history = HistoricalRecords()

    class Meta:
        verbose_name='complemento Usuario'
        verbose_name_plural='complementos Usuario'
        ordering=['-id']

    def __str__(self):
        return f"{self.id_user_fk.username} - {self.perfil_fk.nombre if self.perfil_fk else 'Sin perfil'}"

    def tiene_permiso(self, clave_modulo, accion):
        """
        Verifica si el usuario tiene un permiso específico (leer, crear, actualizar, eliminar) para un módulo.
        'accion' debe ser una de: 'leer', 'crear', 'actualizar', 'eliminar'.
        """
        if not self.perfil_fk:
            return False
        if self.id_user_fk.is_superuser:
            return True

        try:
            permiso = Permiso.objects.get(perfil=self.perfil_fk, modulo__clave=clave_modulo)
            if accion == 'leer':
                return permiso.puede_leer
            elif accion == 'crear':
                return permiso.puede_crear
            elif accion == 'actualizar':
                return permiso.puede_actualizar
            elif accion == 'eliminar':
                return permiso.puede_eliminar
        except Permiso.DoesNotExist:
            return False
        return False


def create_user_tb_usuario(sender, instance, created, **kwargs):
    if created:
        tb_usaurios.objects.create(id_user_fk=instance)

def save_user_tb_usuario(sender, instance, **kwargs):
    if hasattr(instance, 'perfil_usuario'):
        instance.perfil_usuario.save()

# Conectar las señales
post_save.connect(create_user_tb_usuario, sender=User)
post_save.connect(save_user_tb_usuario, sender=User)

#catalogo de los botones/acciones dentro de la paguina
class ct_botones (models.Model):
    nombre = models.CharField(blank=True,max_length=15)
    borrado= models.IntegerField(blank=True,default=1)

#tabla de la bitacora de lo realizado
class tb_bitacora (models.Model):
    #id_usuario = models.ForeignKey(tb_usaurios,editable=True,on_delete=models.CASCADE)
    fecha_hora = models.DateTimeField(auto_now_add=True,auto_now=False)
    url = models.CharField(blank=True,max_length=150)
    id_modulos = models.ForeignKey(ct_modulos,blank=True,editable=True,on_delete=models.CASCADE)
    id_btnaccion=models.ForeignKey(ct_botones,editable=True,on_delete=models.CASCADE)
    borrado = models.IntegerField(blank=True,default=1)

class mainmenu(models.Model):
    menucode = models.IntegerField()
    menuname = models.CharField(max_length=100)
    menutype = models.IntegerField()

    def __str__(self):
        return self.menuname
    
    mainmenulist_objects = models.Manager()

class MenuList(models.Model):
    Menucode = models.IntegerField()
    MenuType = models.IntegerField()
    menuname = models.CharField(max_length=100)
    submenuname=models.CharField(max_length=100)
    menulink = models.CharField(max_length=100)

    def __str__(self):
        return self.menuname
    
    menuList_objects = models.Manager()

# Modelos para Sistema de Documentos Personales
class CategoriaDocumento(models.Model):
    TIPO_CHOICES = [
        ('personal', 'Documento Personal'),
        ('academico', 'Documento Académico'),
        ('admision', 'Documento de Admisión/Aspirante'),
    ]

    nombre = models.CharField(max_length=50)
    descripcion = models.TextField(blank=True, null=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='personal', help_text="Define a qué grupo pertenece la categoría.")
    borrado = models.IntegerField(blank=True, default=1)

    class Meta:
        verbose_name = 'Categoría de Documento'
        verbose_name_plural = 'Categorías de Documentos'
        ordering = ['tipo', 'nombre']

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"

class Aspirante(models.Model):
    """Modelo para almacenar aspirantes anónimos sin cuenta registrada"""
    ESTADO_CHOICES = [
        ('nuevo', 'Nuevo'),
        ('en_revision', 'En Revisión'),
        ('aceptado', 'Aceptado'),
        ('rechazado', 'Rechazado'),
    ]
    
    nombre = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    curp = models.CharField(max_length=18, blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='nuevo')
    observaciones = models.TextField(blank=True, null=True)
    usuario_asignado = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='aspirantes_asignados')
    fecha_ultima_revision = models.DateTimeField(blank=True, null=True)
    borrado = models.IntegerField(blank=True, default=1)
    
    class Meta:
        verbose_name = 'Aspirante'
        verbose_name_plural = 'Aspirantes'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"{self.nombre} {self.apellidos} - {self.email}"
    
    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellidos}"


class DocumentoPersonal(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documentos', null=True, blank=True)
    aspirante = models.ForeignKey(Aspirante, on_delete=models.CASCADE, related_name='documentos', null=True, blank=True)
    categoria = models.ForeignKey(CategoriaDocumento, on_delete=models.CASCADE)
    nombre_documento = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    archivo = models.FileField(upload_to='documentos/%Y/%m/', null=True, blank=True)
    fecha_subida = models.DateTimeField(auto_now_add=True)
    fecha_vencimiento = models.DateField(blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    observaciones = models.TextField(blank=True, null=True)
    borrado = models.IntegerField(blank=True, default=1)
    
    # Campos para el certificado en Blockchain
    certificado_id = models.CharField(max_length=255, blank=True, null=True, help_text="ID del certificado en la blockchain")
    certificado_hash = models.CharField(max_length=255, blank=True, null=True, help_text="Hash de la transacción del certificado en la blockchain")
    fecha_emision_certificado = models.DateTimeField(blank=True, null=True, help_text="Fecha y hora de emisión del certificado")
    
    history = HistoricalRecords()
    
    class Meta:
        verbose_name = 'Documento Personal'
        verbose_name_plural = 'Documentos Personales'
        ordering = ['-fecha_subida']
    
    def __str__(self):
        return f"{self.nombre_documento} - {self.usuario.username}"
    
    @property
    def esta_vencido(self):
        if self.fecha_vencimiento:
            from datetime import date
            return date.today() > self.fecha_vencimiento
        return False

# Modelos para Sistema Académico - Instituciones de Procedencia
class InstitucionProcedencia(models.Model):
    nombre = models.CharField(max_length=200)
    tipo_institucion = models.CharField(max_length=50, choices=[
        ('preparatoria', 'Preparatoria'),
        ('universidad', 'Universidad'),
        ('tecnico', 'Técnico'),
        ('otro', 'Otro'),
    ], default='preparatoria')
    ciudad = models.CharField(max_length=100, blank=True, null=True)
    estado = models.CharField(max_length=100, blank=True, null=True)
    pais = models.CharField(max_length=100, default='México')
    clave_institucion = models.CharField(max_length=50, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    borrado = models.IntegerField(blank=True, default=1)

    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Institución de Procedencia'
        verbose_name_plural = 'Instituciones de Procedencia'
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} - {self.ciudad}, {self.estado}"

# Modelos para Sistema Académico - Cardex de Alumnos
class Carrera(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    codigo_carrera = models.CharField(max_length=20, unique=True)
    borrado = models.IntegerField(blank=True, default=1)

    class Meta:
        verbose_name = 'Carrera'
        verbose_name_plural = 'Carreras'
        ordering = ['nombre']

    def __str__(self):
        return f"{self.codigo_carrera} - {self.nombre}"

class Alumno(models.Model):
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
        ('egresado', 'Egresado'),
        ('baja_temporal', 'Baja Temporal'),
    ]
    
    SEMESTRE_CHOICES = [
        (1, '1er Semestre'),
        (2, '2do Semestre'),
        (3, '3er Semestre'),
        (4, '4to Semestre'),
        (5, '5to Semestre'),
        (6, '6to Semestre'),
        (7, '7mo Semestre'),
        (8, '8vo Semestre'),
        (9, '9no Semestre'),
        (0, 'Semestre Extra'),
    ]

    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='alumno')
    matricula = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    apellido_paterno = models.CharField(max_length=50)
    apellido_materno = models.CharField(max_length=50)
    fecha_nacimiento = models.DateField()
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE, null=True, blank=True)
    institucion_procedencia = models.ForeignKey(InstitucionProcedencia, on_delete=models.SET_NULL, null=True, blank=True, related_name='alumnos')
    semestre_actual = models.IntegerField(default=1, choices=SEMESTRE_CHOICES)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='activo')
    fecha_ingreso = models.DateField(auto_now_add=True)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    email_institucional = models.EmailField(blank=True, null=True)
    curp = models.CharField(max_length=18, unique=True, blank=True, null=True, help_text="Clave Única de Registro de Población")
    borrado = models.IntegerField(blank=True, default=1)
    
    # Campos para el hash único del alumno en Blockchain
    hash_alumno = models.CharField(max_length=255, blank=True, null=True, help_text="Hash único del alumno en la blockchain")
    fecha_emision_hash = models.DateTimeField(blank=True, null=True, help_text="Fecha de emisión del hash del alumno")

    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Alumno'
        verbose_name_plural = 'Alumnos'
        ordering = ['apellido_paterno', 'apellido_materno', 'nombre']

    def __str__(self):
        return f"{self.matricula} - {self.nombre_completo}"

    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido_paterno} {self.apellido_materno}"

    @property
    def promedio_general(self):
        calificaciones = self.calificaciones.filter(borrado=1)
        if calificaciones.exists():
            return calificaciones.aggregate(promedio=models.Avg('calificacion'))['promedio']
        return 0.0

class Materia(models.Model):
    codigo_materia = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    carrera = models.ForeignKey(Carrera, on_delete=models.CASCADE)
    semestre = models.IntegerField()
    creditos = models.IntegerField(default=0)
    borrado = models.IntegerField(blank=True, default=1)

    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Materia'
        verbose_name_plural = 'Materias'
        ordering = ['semestre', 'nombre']

    def __str__(self):
        return f"{self.codigo_materia} - {self.nombre}"

class Calificacion(models.Model):
    ESTADO_CALIFICACION_CHOICES = [
        ('cursando', 'Cursando'),
        ('aprobada', 'Aprobada'),
        ('reprobada', 'Reprobada'),
        ('especial', 'Especial'),
    ]

    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, related_name='calificaciones')
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    calificacion = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CALIFICACION_CHOICES, default='cursando')
    periodo = models.CharField(max_length=50)  # Ej: "2024-1", "2024-2"
    fecha_registro = models.DateTimeField(auto_now_add=True)
    profesor = models.CharField(max_length=100, blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    borrado = models.IntegerField(blank=True, default=1)

    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Calificación'
        verbose_name_plural = 'Calificaciones'
        ordering = ['-fecha_registro']
        unique_together = ['alumno', 'materia', 'periodo']

    def __str__(self):
        return f"{self.alumno.nombre_completo} - {self.materia.nombre} - {self.calificacion or 'Sin calificar'}"

class DocumentoAcademico(models.Model):
    TIPO_DOCUMENTO_CHOICES = [
        ('certificado', 'Certificado'),
        ('constancia', 'Constancia'),
        ('boleta', 'Boleta de Calificaciones'),
        ('historial', 'Historial Académico'),
        # Documentos de Titulación
        ('titulo', 'Título Profesional'),
        ('cedula', 'Cédula Profesional'),
        ('acta_examen', 'Acta de Examen Profesional'),
        ('liberacion_ss', 'Liberación de Servicio Social'),
        ('otro', 'Otro'),
    ]

    ESTADO_REVISION_CHOICES = [
        ('pendiente', 'Pendiente de Revisión'),
        ('en_revision', 'En Revisión'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
        ('corregido', 'Requiere Correcciones'),
    ]

    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, related_name='documentos_academicos')
    tipo_documento = models.CharField(max_length=20, choices=TIPO_DOCUMENTO_CHOICES)
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    archivo = models.FileField(upload_to='documentos_academicos/%Y/%m/', null=True, blank=True)
    fecha_subida = models.DateTimeField(auto_now_add=True)
    estado_revision = models.CharField(max_length=20, choices=ESTADO_REVISION_CHOICES, default='pendiente')
    revisado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='documentos_revisados')
    fecha_revision = models.DateTimeField(blank=True, null=True)
    comentarios_revision = models.TextField(blank=True, null=True)
    periodo_academico = models.CharField(max_length=50, blank=True, null=True)
    borrado = models.IntegerField(blank=True, default=1)

    # Campos para el certificado en Blockchain
    certificado_id = models.CharField(max_length=255, blank=True, null=True, help_text="ID del certificado en la blockchain")
    certificado_hash = models.CharField(max_length=255, blank=True, null=True, help_text="Hash de la transacción del certificado en la blockchain")
    fecha_emision_certificado = models.DateTimeField(blank=True, null=True, help_text="Fecha y hora de emisión del certificado")

    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Documento Académico'
        verbose_name_plural = 'Documentos Académicos'
        ordering = ['-fecha_subida']

    def __str__(self):
        return f"{self.alumno.nombre_completo} - {self.titulo}"

    def aprobar_documento(self, revisor, comentarios=''):
        """Método para aprobar un documento"""
        self.estado_revision = 'aprobado'
        self.revisado_por = revisor
        self.fecha_revision = timezone.now()
        self.comentarios_revision = comentarios
        self.save()

    def rechazar_documento(self, revisor, comentarios=''):
        """Método para rechazar un documento"""
        self.estado_revision = 'rechazado'
        self.revisado_por = revisor
        self.fecha_revision = timezone.now()
        self.comentarios_revision = comentarios
        self.save()

# Modelos para Sistema de Inventario/Productos
class CategoriaProducto(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    borrado = models.IntegerField(blank=True, default=1)

    class Meta:
        verbose_name = 'Categoría de Producto'
        verbose_name_plural = 'Categorías de Productos'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    categoria = models.ForeignKey(CategoriaProducto, on_delete=models.CASCADE)
    precio = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock = models.IntegerField(default=0)
    stock_minimo = models.IntegerField(default=0)
    borrado = models.IntegerField(blank=True, default=1)

    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} - {self.categoria.nombre}"

    @property
    def stock_disponible(self):
        return self.stock

    @property
    def necesita_reabastecimiento(self):
        return self.stock <= self.stock_minimo

class MovimientoCardex(models.Model):
    TIPO_MOVIMIENTO_CHOICES = [
        ('entrada', 'Entrada'),
        ('salida', 'Salida'),
        ('ajuste', 'Ajuste'),
    ]

    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='movimientos')
    tipo_movimiento = models.CharField(max_length=20, choices=TIPO_MOVIMIENTO_CHOICES)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    fecha_movimiento = models.DateTimeField(auto_now_add=True)
    descripcion = models.TextField(blank=True, null=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    documento_referencia = models.CharField(max_length=50, blank=True, null=True)
    borrado = models.IntegerField(blank=True, default=1)

    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Movimiento de Cardex'
        verbose_name_plural = 'Movimientos de Cardex'
        ordering = ['-fecha_movimiento']

    def __str__(self):
        return f"{self.tipo_movimiento} - {self.producto.nombre} - {self.cantidad}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Actualizar stock del producto
        if self.tipo_movimiento == 'entrada':
            self.producto.stock += self.cantidad
        elif self.tipo_movimiento == 'salida':
            self.producto.stock -= self.cantidad
        elif self.tipo_movimiento == 'ajuste':
            # Para ajustes, la cantidad puede ser positiva o negativa
            self.producto.stock += self.cantidad
        self.producto.save()

class Inventario(models.Model):
    producto = models.OneToOneField(Producto, on_delete=models.CASCADE, related_name='inventario')
    cantidad_actual = models.IntegerField(default=0)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    ubicacion = models.CharField(max_length=100, blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    borrado = models.IntegerField(blank=True, default=1)

    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Inventario'
        verbose_name_plural = 'Inventarios'
        ordering = ['producto__nombre']

    def __str__(self):
        return f"Inventario - {self.producto.nombre}"

#class emitCertificado(models.Model):
