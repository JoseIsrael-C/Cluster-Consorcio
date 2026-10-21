# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('management', '0007_remove_ct_modulos_id_perfil_fk_ct_modulos_clave_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='alumno',
            name='curp',
            field=models.CharField(blank=True, help_text='Clave Única de Registro de Población', max_length=18, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='alumno',
            name='hash_alumno',
            field=models.CharField(blank=True, help_text='Hash único del alumno en la blockchain', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='alumno',
            name='fecha_emision_hash',
            field=models.DateTimeField(blank=True, help_text='Fecha de emisión del hash del alumno', null=True),
        ),
    ]

