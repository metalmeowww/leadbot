import csv

from django.contrib import admin
from django.http import HttpResponse

from .models import Business, Question, Lead


class QuestionInline(admin.TabularInline):
    """Вопросы редактируются прямо внутри карточки бизнеса"""
    model = Question
    extra = 1
    fields = ('order', 'text', 'field_name', 'options', 'is_required')

@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ('name', 'telegram_id', 'is_active', 'created_at') 
    list_filter = ('is_active',)
    search_fields = ('name',)
    inlines = [QuestionInline]

@admin.register(Question)
class QuestionsAdmin(admin.ModelAdmin):
    list_display = ('business', 'order', 'text', 'field_name', 'is_required')
    list_filter = ('business', 'is_required')
    ordering = ('business', 'order')
    fields = ('business', 'order', 'text', 'field_name', 'options', 'is_required')


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'service', 'status', 'business', 'created_at')
    list_filter = ('status', 'business', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['export_to_csv']

    @admin.action(description='Экспорт выбранных заявок в CSV')
    def export_to_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="leads.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow(['Имя', 'Телефон', 'Услуга', 'Комментарий', 'Статус', 'Дата'])

        for lead in queryset:
            writer.writerow([
                lead.name,
                lead.phone,
                lead.service,
                lead.message,
                lead.get_status_display(),
                lead.created_at.strftime('%d.%m.%Y %H:%M'),
            ])
        return response
