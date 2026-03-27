from django.contrib.auth import authenticate
from rest_framework import serializers


class CurrentUserSerializer(serializers.Serializer):
    id           = serializers.IntegerField(source='pk')
    username     = serializers.CharField()
    email        = serializers.EmailField()
    first_name   = serializers.CharField()
    last_name    = serializers.CharField()
    full_name    = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    bio          = serializers.SerializerMethodField()
    avatar       = serializers.SerializerMethodField()

    def get_full_name(self, user) -> str:
        return user.get_full_name()

    def get_display_name(self, user) -> str:
        try:
            return user.profile.display_name or user.get_full_name() or user.username
        except Exception:
            return user.get_full_name() or user.username

    def get_bio(self, user) -> str:
        try:
            return user.profile.bio
        except Exception:
            return ''

    def get_avatar(self, user) -> str | None:
        try:
            av = user.profile.avatar
            return av.url if av else None
        except Exception:
            return None


class ProfileUpdateSerializer(serializers.Serializer):
    """PATCH /api/accounts/me/ — update editable profile fields."""
    first_name   = serializers.CharField(required=False, allow_blank=True)
    last_name    = serializers.CharField(required=False, allow_blank=True)
    display_name = serializers.CharField(required=False, allow_blank=True)
    bio          = serializers.CharField(required=False, allow_blank=True)

    def update(self, user, validated_data):
        user_dirty = False
        if 'first_name' in validated_data:
            user.first_name = validated_data['first_name']
            user_dirty = True
        if 'last_name' in validated_data:
            user.last_name = validated_data['last_name']
            user_dirty = True
        if user_dirty:
            user.save(update_fields=[f for f in ('first_name', 'last_name') if f in validated_data])

        profile_fields = {}
        if 'display_name' in validated_data:
            profile_fields['display_name'] = validated_data['display_name']
        if 'bio' in validated_data:
            profile_fields['bio'] = validated_data['bio']
        if profile_fields:
            user.profile.__dict__.update(profile_fields)
            user.profile.save(update_fields=list(profile_fields.keys()))

        return user


class ChangePasswordSerializer(serializers.Serializer):
    """POST /api/accounts/me/password/"""
    current_password = serializers.CharField()
    new_password     = serializers.CharField(min_length=8)
    confirm_password = serializers.CharField()

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        return data

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not authenticate(username=user.username, password=value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value


class ChangeEmailSerializer(serializers.Serializer):
    """POST /api/accounts/me/email/"""
    new_email        = serializers.EmailField()
    current_password = serializers.CharField()

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not authenticate(username=user.username, password=value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value