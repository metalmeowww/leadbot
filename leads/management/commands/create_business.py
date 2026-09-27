from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from leads.models import Business, Question

class Command(BaseCommand):
    help = 'Создаёт новый бизнес с набором стандартных вопросов'

    def add_arguments(self, parser):
        parser.add_argument('name', type=str, help='Название бизнеса')
        parser.add_argument(
            '--username',
            type=str,
            default=None,
            help='Username владельца (если не указан - первый суперпользователь)',
        )
    
    def handle(self, *args, **options):
        business_name = options['name']
        username = options['username']

        # Находим владельца
        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                raise CommandError(f'Пользователь "{username}" не найден')
        else:
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                raise CommandError('Нет ни одного суперпользователя. Создайте его.')

        # Создаём бизнес
        business = Business.objects.create(
            user=user,
            name=business_name,
            greeting='👋 Здравствуйте! Рады видеть вас.\n'
                     'Ответьте на несколько коротких вопросов — '
                     'и мы свяжемся с вами в течение 15 минут.',
            about_text='Информация о компании скоро появится.',
            contacts_text='📞 Телефон: +7 900 000-00-00\n'
                          '📍 Адрес: ул. Примерная, 1\n'
                          '✉️ Telegram: @example',
            thank_you_text='✅ Спасибо! Ваша заявка принята.\n'
                           'Мы свяжемся с вами в ближайшее время.',
        )

        # Создаём 4 стандартных вопроса
        Question.objects.create(
            business=business, order=1,
            text='👤 Как вас зовут?',
            field_name='name', is_required=True,
        )
        Question.objects.create(
            business=business, order=2,
            text='📞 Ваш номер телефона?',
            field_name='phone', is_required=True,
        )
        Question.objects.create(
            business=business, order=3,
            text='💼 Какую услугу рассматриваете?',
            field_name='service', is_required=True,
            options=['Услуга 1', 'Услуга 2', 'Услуга 3', 'Услуга 4'],
        )
        Question.objects.create(
            business=business, order=4,
            text='💬 Есть пожелания? Напишите или нажмите «Нет комментариев»',
            field_name='message', is_required=False,
            options=['Нет комментариев'],
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Бизнес "{business_name}" создан!\n'
                f'  Владелец: {user.username}\n'
                f'  Вопросов: 4\n'
                f'  Откройте админку и заполните "О нас" и "Контакты".'
            )
        )