# pipeline/serializers.py
from rest_framework import serializers
from .models import Project

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        # Le decimos: "Traduce todos los campos que existan en el modelo"
        fields = '__all__'