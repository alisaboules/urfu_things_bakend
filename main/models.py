from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator

# Кастомная модель пользователя (соответствует SQL таблице users)
class User(AbstractUser):
    ROLE_CHOICES = [
        ('student', 'Студент'),
        ('pickup_point', 'Сотрудник пункта выдачи'),
        ('admin', 'Администратор'),
    ]
    
    # Переопределяем поля для соответствия SQL
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(max_length=100, unique=True)
    first_name = models.CharField(max_length=100, verbose_name='full_name')
    last_name = models.CharField(max_length=100, blank=True)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='student')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Дополнительные поля
    phone = models.CharField(max_length=20, blank=True, null=True)
    group_number = models.CharField(max_length=20, blank=True, null=True)
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'first_name']
    
    class Meta:
        db_table = 'users'  # Соответствует SQL таблице
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
    
    def __str__(self):
        return self.first_name


class Role(models.Model):
    """Роли пользователей (соответствует SQL таблице role)"""
    name = models.CharField(max_length=50, unique=True)
    
    class Meta:
        db_table = 'role'
        verbose_name = 'Роль'
        verbose_name_plural = 'Роли'
    
    def __str__(self):
        return self.name


class Building(models.Model):
    """Корпуса университета"""
    name = models.CharField(max_length=50, unique=True)
    address = models.CharField(max_length=100, blank=True, null=True)
    
    class Meta:
        db_table = 'building'
        verbose_name = 'Корпус'
        verbose_name_plural = 'Корпуса'
    
    def __str__(self):
        return self.name


class Category(models.Model):
    """Категории вещей (с поддержкой вложенности)"""
    name = models.CharField(max_length=50, unique=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, db_column='parent_cat_id')
    
    class Meta:
        db_table = 'category'
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
    
    def __str__(self):
        return self.name


class PickupPoint(models.Model):
    """Пункты выдачи"""
    name = models.CharField(max_length=50)
    location = models.CharField(max_length=100, blank=True, null=True)
    building = models.ForeignKey(Building, on_delete=models.RESTRICT, db_column='building_id')
    
    class Meta:
        db_table = 'pickup_point'
        verbose_name = 'Пункт выдачи'
        verbose_name_plural = 'Пункты выдачи'
    
    def __str__(self):
        return self.name


class FoundItem(models.Model):
    category = models.ForeignKey(
    Category,
    on_delete=models.RESTRICT,
    null=True,
    blank=True
)

    pickup_point = models.ForeignKey(
    PickupPoint,
    on_delete=models.RESTRICT,
    null=True,
    blank=True
)
#     image = models.ImageField(
#     upload_to='items/',
#     blank=True,
#     null=True
# )


    """Находки"""
    LOCATION_TYPE_CHOICES = [
        ('building', 'Здание'),
        ('map', 'Карта'),
        ('free', 'Свободное описание'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Активна'),
        ('in_pickup', 'В пункте выдачи'),
        ('has_match', 'Есть совпадение'),
        ('issued', 'Выдана'),
        ('closed', 'Закрыта'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id', related_name='found_items')
    # category = models.ForeignKey(Category, on_delete=models.RESTRICT, db_column='category_id')
    # pickup_point = models.ForeignKey(PickupPoint, on_delete=models.RESTRICT, db_column='pickup_point_id')
    location_type = models.CharField(max_length=20, choices=LOCATION_TYPE_CHOICES, blank=True, null=True)
    location_ref = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to='found_items/', null=True, blank=True)

    class Meta:
        db_table = 'found_item'
        verbose_name = 'Находка'
        verbose_name_plural = 'Находки'
    
    def __str__(self):
        return f"Найдено: {self.category.name if self.category else '?'} (ID: {self.found_id})"


class LostItem(models.Model):
    image = models.ImageField(
    upload_to='items/',
    blank=True,
    null=True
)
    category = models.ForeignKey(
    Category,
    on_delete=models.RESTRICT,
    db_column='category_id',
    null=True,
    blank=True
)


    """Пропажи"""
    STATUS_CHOICES = [
        ('active', 'Активна'),
        ('has_match', 'Есть совпадение'),
        ('closed', 'Закрыта'),
        ('disputed', 'Спорная ситуация'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id', related_name='lost_items')
    location_zone = models.CharField(max_length=50, blank=True, null=True)
    location_text = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'lost_item'
        verbose_name = 'Пропажа'
        verbose_name_plural = 'Пропажи'
    
    def __str__(self):
        return f"Потеряно: {self.category.name if self.category else '?'} (ID: {self.lost_id})"


class Photo(models.Model):
    """Фото (связь либо с находкой, либо с пропажей)"""
    found_item = models.ForeignKey(FoundItem, on_delete=models.CASCADE, db_column='found_id', null=True, blank=True, related_name='photos')
    lost_item = models.ForeignKey(LostItem, on_delete=models.CASCADE, db_column='lost_id', null=True, blank=True, related_name='photos')
    image_url = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'photo'
        verbose_name = 'Фото'
        verbose_name_plural = 'Фото'
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.found_item and not self.lost_item:
            raise ValidationError('Фото должно быть связано либо с находкой, либо с пропажей')


class Match(models.Model):
    """Сопоставления находок и пропаж"""
    STATUS_CHOICES = [
        ('pending', 'На рассмотрении'),
        ('confirmed', 'Подтверждено'),
        ('rejected', 'Отклонено'),
    ]
    
    found_item = models.ForeignKey(FoundItem, on_delete=models.CASCADE, db_column='found_id', related_name='matches')
    lost_item = models.ForeignKey(LostItem, on_delete=models.CASCADE, db_column='lost_id', related_name='matches')
    similarity_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'match'
        verbose_name = 'Сопоставление'
        verbose_name_plural = 'Сопоставления'


class Issuance(models.Model):
    """Выдача вещей"""
    found_item = models.OneToOneField(
        'FoundItem', 
        on_delete=models.CASCADE, 
        related_name='issuance',
        verbose_name='Находка'
    )
    pickup_point = models.ForeignKey(
        'PickupPoint', 
        on_delete=models.RESTRICT, 
        related_name='issuances',
        verbose_name='Пункт выдачи'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.RESTRICT, 
        related_name='issuances',
        verbose_name='Получатель'
    )
    issued_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата выдачи')
    verified_by = models.CharField(max_length=100, blank=True, null=True, verbose_name='Кто выдал')
    
    class Meta:
        db_table = 'issuance'
        verbose_name = 'Выдача'
        verbose_name_plural = 'Выдачи'
    
    def __str__(self):
        return f"Выдача {self.found_item} - {self.user}"


class Log(models.Model):
    """Логи действий"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='logs', verbose_name='Пользователь')
    action_type = models.CharField(max_length=50, verbose_name='Тип действия')
    entity_type = models.CharField(max_length=50, verbose_name='Тип сущности')
    entity_id = models.IntegerField(verbose_name='ID сущности')
    action_data = models.TextField(blank=True, null=True, verbose_name='Данные действия')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата и время')
    ip_address = models.CharField(max_length=45, blank=True, null=True, verbose_name='IP адрес')
    
    class Meta:
        db_table = 'log'
        verbose_name = 'Лог'
        verbose_name_plural = 'Логи'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.created_at} - {self.user} - {self.action_type}"