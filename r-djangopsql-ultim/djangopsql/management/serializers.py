from rest_framework import serializers
from .models import MenuList

class menuserializer(serializers.ModelSerializer):
    class Meta:
        model = MenuList
        fields = ['menuname']

class submenuserializer(serializers.ModelSerializer):
    class Meta:
        model = MenuList
        fields = ['menuname', 'submenuname', 'menulink', 'MenuType']