from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import (
    User, Category, PickupPoint, FoundItem, LostItem, 
    Building, Photo, Match, Issuance, Log
)


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='first_name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone', 'role', 'created_at', 'full_name']


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
        fields = ['id', 'name', 'location', 'building', 'building_name']


class PhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Photo
        fields = ['id', 'image_url', 'uploaded_at']


# class FoundItemSerializer(serializers.ModelSerializer):
#     user_username = serializers.ReadOnlyField(source='user.username')
#     category_name = serializers.ReadOnlyField(source='category.name')
#     pickup_point_name = serializers.ReadOnlyField(source='pickup_point.name')
#     photos = PhotoSerializer(many=True, read_only=True)
    
#     class Meta:
#         model = FoundItem
#         fields = ['id', 'user', 'user_username', 'category', 'category_name', 
#                   'pickup_point', 'pickup_point_name', 'location_type', 'location_ref',
#                   'description', 'status', 'created_at', 'photos']
#         read_only_fields = ['user', 'created_at']

class FoundItemSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        required=False,
        allow_null=True,
        default=None
    )

    pickup_point = serializers.PrimaryKeyRelatedField(
        queryset=PickupPoint.objects.all(),
        required=False,
        allow_null=True,
        default=None
    )
    image = serializers.ImageField(required=False)


    class Meta:
        model = FoundItem
        fields = [
            'id', 'user',
            'category', 'pickup_point',
            'location_type', 'location_ref',
            'description', 'status', 'created_at', 'image'
        ]
        read_only_fields = ['user', 'created_at']

class LostItemSerializer(serializers.ModelSerializer):
    user_username = serializers.ReadOnlyField(source='user.username')
    category_name = serializers.ReadOnlyField(source='category.name')
    photos = PhotoSerializer(many=True, read_only=True)
    
    class Meta:
        model = LostItem
        fields = ['id', 'user', 'user_username', 'category', 'category_name', 
                  'location_zone', 'location_text', 'description', 'status', 
                  'created_at', 'photos']
        read_only_fields = ['user', 'created_at']


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

class IssuanceSerializer(serializers.ModelSerializer):
    found_item_title = serializers.ReadOnlyField(source='found_item.title')
    pickup_point_name = serializers.ReadOnlyField(source='pickup_point.name')
    user_username = serializers.ReadOnlyField(source='user.username')
    
    class Meta:
        model = Issuance
        fields = ['id', 'found_item', 'found_item_title', 'pickup_point', 
                  'pickup_point_name', 'user', 'user_username', 'issued_at', 'verified_by']
        read_only_fields = ['issued_at']


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
