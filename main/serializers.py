from rest_framework import serializers
from .models import Notification
from django.contrib.auth.password_validation import validate_password
from .models import (
    User, Category, PickupPoint, FoundItem, LostItem, 
    Building, Photo, Match, Issuance, Log, Appeal, SearchHistory
)
from .models import SearchHistory

class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='first_name', read_only=True)
    avatar = serializers.SerializerMethodField()
    pickup_point_name = serializers.CharField(source='pickup_point.name', read_only=True, allow_null=True)
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone', 'role', 'created_at', 'full_name', 'avatar',   "notifications_enabled",
            "fcm_token", 'student_id', 'pickup_point', 'pickup_point_name'
        ]

    def get_avatar(self, obj):
        if not obj.avatar:
            return None

        request = self.context.get('request')

        if request:
            return request.build_absolute_uri(obj.avatar.url)

        return obj.avatar.url
    
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ['username', 'password', 'password2', 'email', 'first_name', 'last_name', 'phone']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Пароли не совпадают"})
        return attrs
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует")
        return value
    
    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        user.role = 'student'  # По умолчанию студент
        user.save()
        return user


class BuildingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Building
        fields = ['id', 'name', 'address']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'parent']


class PickupPointSerializer(serializers.ModelSerializer):
    building_name = serializers.ReadOnlyField(source='building.name')
    
    class Meta:
        model = PickupPoint
        fields = ['id', 'name', 'location', 'building', 'building_name', 'address', 'latitude', 'longitude']


class PhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Photo
        fields = ['id', 'image_url', 'uploaded_at']


class FoundItemSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source='user.first_name', read_only=True)
    category_name = serializers.ReadOnlyField(source='category.name')
    category = serializers.PrimaryKeyRelatedField(
    queryset=Category.objects.all()
    )
    pickup_point = serializers.PrimaryKeyRelatedField(
    queryset=PickupPoint.objects.all(),
    required=False,
    allow_null=True
    )

    pickup_point_name = serializers.CharField(
        source='pickup_point.name',
        read_only=True
    )
    class Meta:
        model = FoundItem
        fields = [
            'id',
            'title',
            'user',
            'category',
            'category_name',
            'pickup_point',
            'location_type',
            'location_ref',
            'description',
            'status',
            'created_at',
            'image',
            'author',
            'pickup_point_name',
        ]
        read_only_fields = ['user', 'created_at']

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.image:
            data['image'] = instance.image.url

        return data
    
    def get_image(self, obj):
        if not obj.image:
            return None
        return obj.image.url
   

class LostItemSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source='user.first_name', read_only=True)
    user_username = serializers.ReadOnlyField(source='user.username')
    category_name = serializers.ReadOnlyField(source='category.name')
    photos = PhotoSerializer(many=True, read_only=True)
    # category = serializers.PrimaryKeyRelatedField(
    #     queryset=Category.objects.all(),
    #     required=False,
    #     allow_null=True
    # )
    category = serializers.PrimaryKeyRelatedField(
    queryset=Category.objects.all()
    )
    pickup_point = serializers.PrimaryKeyRelatedField(
    queryset=PickupPoint.objects.all(),
    required=False,
    allow_null=True
    )

    pickup_point_name = serializers.CharField(
        source='pickup_point.name',
        read_only=True
    )
    class Meta:
        model = LostItem
        fields = ['id', 'title', 'user', 'user_username', 'category', 'category_name', 
                  'location_zone', 'location_text', 'description', 'status', 
                  'created_at', 'photos', 'image', 'author', 'pickup_point_name', 'pickup_point']
        read_only_fields = ['user', 'created_at']
        
    def get_image(self, obj):
        if not obj.image:
            return None

        request = self.context.get('request')

        if request:
            return request.build_absolute_uri(obj.image.url)

        return obj.image.url


class MatchSerializer(serializers.ModelSerializer):
    found_item_details = FoundItemSerializer(source='found_item', read_only=True)
    lost_item_details = LostItemSerializer(source='lost_item', read_only=True)
    
    class Meta:
        model = Match
        fields = ['id', 'found_item', 'lost_item', 'similarity_pct', 'status', 'created_at', 
                  'found_item_details', 'lost_item_details']
        
class FoundItemStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=FoundItem.STATUS_CHOICES)
    
    def validate_status(self, value):
        # Дополнительная валидация статусов
        return value

class LostItemStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=LostItem.STATUS_CHOICES)

# class IssuanceSerializer(serializers.ModelSerializer):
#     found_item_title = serializers.ReadOnlyField(source='found_item.description')
#     pickup_point_name = serializers.ReadOnlyField(source='pickup_point.name')
#     user_username = serializers.ReadOnlyField(source='user.username')
    
#     class Meta:
#         model = Issuance
#         fields = ['id', 'found_item', 'found_item_title', 'pickup_point', 
#                   'pickup_point_name', 'user', 'user_username', 'issued_at', 'verified_by']
#         read_only_fields = ['issued_at']
class IssuanceSerializer(serializers.ModelSerializer):
    found_item_title = serializers.ReadOnlyField(source='found_item.title')
    found_item_description = serializers.ReadOnlyField(source='found_item.description')
    found_item_image = serializers.SerializerMethodField()
    found_item_location = serializers.ReadOnlyField(source='found_item.location_ref')
    found_item_author = serializers.ReadOnlyField(source='found_item.user.username')
    found_item_created_at = serializers.ReadOnlyField(source='found_item.created_at')
    pickup_point_name = serializers.CharField(source='pickup_point.name', read_only=True)
    user_username = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = Issuance
        fields = [
            'id',
            'found_item',
            'found_item_title',
            'found_item_description',
            'found_item_image',
            'found_item_location',
            'found_item_author',
            'found_item_created_at',
            'pickup_point',
            'pickup_point_name',
            'user',
            'user_username',
            'issued_at',
            'verified_by',
        ]
    def get_found_item_image(self, obj):
        image = obj.found_item.image
        if image:
            try:
                return image.url
            except ValueError:
                return None
        return None

class ConfirmIssuanceSerializer(serializers.Serializer):
    """Сериализатор для подтверждения выдачи"""
    found_item_id = serializers.IntegerField()
    user_id = serializers.IntegerField()
    verified_by = serializers.CharField(max_length=100, required=False, allow_blank=True)
    
class LogSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source='user.username')
    user_role = serializers.ReadOnlyField(source='user.role')
    
    class Meta:
        model = Log
        fields = ['id', 'user', 'username', 'user_role', 'action_type', 
                  'entity_type', 'entity_id', 'action_data', 'created_at', 'ip_address']


class NearestPickupPointSerializer(serializers.Serializer):
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()


class PickupPointWithDistanceSerializer(PickupPointSerializer):
    distance_km = serializers.FloatField(read_only=True)
    
    class Meta(PickupPointSerializer.Meta):
        fields = PickupPointSerializer.Meta.fields + ['distance_km', 'latitude', 'longitude', 'address']

class MyItemStatusSerializer(serializers.Serializer):
    """Сериализатор для статусов объявлений пользователя"""
    id = serializers.IntegerField()
    title = serializers.CharField()
    type = serializers.CharField()  # 'found' или 'lost'
    status = serializers.CharField()
    status_display = serializers.CharField()
    category_name = serializers.CharField()
    location = serializers.CharField()
    created_at = serializers.DateTimeField()
    photo_url = serializers.URLField(allow_null=True)

class AppealSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source='user.username')
    found_item_title = serializers.ReadOnlyField(source='found_item.title', allow_null=True)
    lost_item_title = serializers.ReadOnlyField(source='lost_item.title', allow_null=True)
    
    class Meta:
        model = Appeal
        fields = ['id', 'user', 'username', 'found_item', 'found_item_title', 
                  'lost_item', 'lost_item_title', 'subject', 'message', 
                  'status', 'admin_comment', 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at']


class AppealCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appeal
        fields = ['found_item', 'lost_item', 'subject', 'message']
    
    def validate(self, data):
        if not data.get('found_item') and not data.get('lost_item'):
            raise serializers.ValidationError("Укажите либо находку, либо пропажу")
        return data


class AppealUpdateSerializer(serializers.ModelSerializer):
    """Для администратора: обновление статуса и ответа"""
    class Meta:
        model = Appeal
        fields = ['status', 'admin_comment']

class SearchHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchHistory
        fields = ['id', 'query', 'created_at']

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ['id', 'action_time', 'is_read', 'user']