from django.contrib import admin

from .models import Message, Thread, ThreadParticipant


class ThreadParticipantInline(admin.TabularInline):
    model = ThreadParticipant
    extra = 0
    readonly_fields = ('joined_at', 'last_read_at')


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('sent_at',)


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display  = ('id', 'thread_type', 'subject', 'course', 'created_by', 'last_message_at', 'created_at')
    list_filter   = ('thread_type',)
    search_fields = ('subject',)
    inlines       = [ThreadParticipantInline, MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display  = ('id', 'thread', 'sender', 'message_type', 'sent_at')
    list_filter   = ('message_type',)
    search_fields = ('body',)


@admin.register(ThreadParticipant)
class ThreadParticipantAdmin(admin.ModelAdmin):
    list_display = ('thread', 'user', 'folder', 'is_starred', 'last_read_at', 'joined_at')
    list_filter  = ('folder', 'is_starred')