from rest_framework import serializers
from .models import Version, Project

class VersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Version
        fields = ['id', 'version_number', 'approval_status', 'transcoding_status', 'original_file_path', 'created_at']
        read_only_fields = ['id', 'version_number', 'approval_status', 'transcoding_status', 'created_at']