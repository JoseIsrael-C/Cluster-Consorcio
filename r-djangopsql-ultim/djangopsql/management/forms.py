from django import forms
from management.models import ct_modulos, ct_submodulos, ct_perfil

class CrearMenu(forms.ModelForm):
    id_perfil_fk = forms.ModelMultipleChoiceField(
        queryset = ct_perfil.objects.all(),
        widget = forms.CheckboxSelectMultiple,
        required=False
    )
    class Meta:
        model = ct_modulos
        #fields = '__all__'
        fields = ['nombre','url','borrado','id_perfil_fk']

class CrearSubMenu(forms.ModelForm):
    class Meta:
        model = ct_submodulos
        fields = '__all__'