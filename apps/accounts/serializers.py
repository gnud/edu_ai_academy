from rest_framework import serializers


class CurrentUserSerializer(serializers.Serializer):
    id           = serializers.IntegerField(source='pk')
    username     = serializers.CharField()
    email        = serializers.EmailField()
    full_name    = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    avatar       = serializers.SerializerMethodField()

    def get_full_name(self, user) -> str:
        return user.get_full_name()

    def get_display_name(self, user) -> str:
        try:
            return user.profile.display_name or user.get_full_name() or user.username
        except Exception:
            return user.get_full_name() or user.username

    def get_avatar(self, user) -> str | None:
        try:
            av = user.profile.avatar
            return av.url if av else None
        except Exception:
            return None