from rest_framework import serializers
from .models import Version, Project, Asset, User

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = '__all__'

class AssetSerializer(serializers.ModelSerializer):
    # Mostramos el nombre del proyecto en lugar de solo el ID
    project_title = serializers.ReadOnlyField(source='project.title')

    class Meta:
        model = Asset
        fields = ['id', 'name', 'category', 'project', 'project_title', 'checksum_sha256']
        read_only_fields = ['checksum_sha256']

class VersionSerializer(serializers.ModelSerializer):
    # Metadata técnica (ReadOnly porque la extrae tu lógica de FFmpeg/ingest)
    asset_name = serializers.ReadOnlyField(source='asset.name')
    
    class Meta:
        model = Version
        fields = [
            'id', 'asset', 'asset_name', 'department', 'version_number', 
            'file', 'uploaded_by', 'approval_status',
            'resolution_width', 'resolution_height', 'fps', 'duration',
            'filesize', 'transcoding_status', 'created_at'
        ]
        # Estos campos los llena tu modelo automáticamente o el worker
        read_only_fields = [
            'id', 'version_number', 'filesize', 'resolution_width', 
            'resolution_height', 'fps', 'duration', 'transcoding_status', 
            'created_at'
        ]

    def validate(self, data):
        """
        Este es el 'escudo' del Serializer. 
        Forzamos a que corra el clean() del modelo para que tu lógica de 
        bloqueo de hashes duplicados funcione antes de guardar.
        """
        instance = Version(**data)
        try:
            # Aquí invocamos tu lógica de SHA-256 y QC
            instance.clean()
        except serializers.ValidationError as e:
            raise e
        except Exception as e:
            raise serializers.ValidationError(str(e))
        return data