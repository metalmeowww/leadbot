from django.db import models
from django.contrib.auth.models import User

class Business(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='business',
        verbose_name='Пользователь'
    )
    name = models.CharField('Название бизнеса', max_length=200)
    telegram_id = models.BigIntegerField(
        'Telegram ID владельца', unique=True, null=True, blank=True
    )
    greeting = models.TextField(
        'Приветствие бота',
        default='Здравствуйте! Ответьте на несколько вопросов, и мы свяжемся с вами.'
    )
    is_active = models.BooleanField('Активен', default=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Бизнес'
        verbose_name_plural = 'Бизнесы'

    def __str__(self):
        return self.name

class Question(models.Model):
    business = models.ForeignKey(
        Business, on_delete=models.CASCADE, related_name='questions',
        verbose_name ='Бизнес'
    )
    text = models.CharField('Текст вопроса', max_length=300)
    field_name = models.CharField(
        'Поле',
        max_length=50,
        help_text='Куда сохранять: name, phone, service, message, budget'
    )
    order = models.PositiveIntegerField('Порядок', default=0)
    is_required = models.BooleanField('Обязательный', default=True)

    class Meta:
        ordering = ['order']
        verbose_name = 'Вопрос'
        verbose_name_plural = 'Вопросы'

    def __str__(self):
        return f'{self.order}. {self.text}'


class Lead(models.Model):
    """Заявка от клиента"""
    STATUS_CHOICES = [
        ('new', 'Новая'),
        ('in_progress', 'В работе'),
        ('done', 'Обработана'),
        ('cancelled', 'Отменена'),
    ]

    business = models.ForeignKey(
        Business, on_delete=models.CASCADE, related_name='leads',
        verbose_name='Бизнес'
    )
    client_telegram_id = models.BigIntegerField(
        'Telegram ID клиента', null=True, blank=True
    )
    client_username = models.CharField(
        'Username клиента', max_length=100, blank=True
    )

    name = models.CharField('Имя', max_length=100, blank=True)
    phone = models.CharField('Телефон', max_length=30, blank=True)
    service = models.CharField('Услуга', max_length=200, blank=True)
    message = models.TextField('Комментарий', blank=True)
    budget = models.CharField('Бюджет', max_length=100, blank=True)

    status = models.CharField(
        'Статус', max_length=20, choices=STATUS_CHOICES, default='new'
    )
    created_at = models.DateTimeField('Создана', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлена', auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Заявка'
        verbose_name_plural = 'Заявки'

    def __str__(self):
        return f'{self.name or "Без имени"} - {self.phone or "без телефона"}'