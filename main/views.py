from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend # type: ignore
from rest_framework import filters as drf_filters
from .models import Appeal, Category, Log, PickupPoint, FoundItem, LostItem, User
from django.db.models import Q
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from firebase_admin import messaging
from .utils import find_matches, get_nearest_pickup_point, calculate_distance
from rest_framework.pagination import PageNumberPagination
from .serializers import (
    AppealCreateSerializer, AppealSerializer, AppealUpdateSerializer, CategorySerializer, LogSerializer, PickupPointSerializer, 
    FoundItemSerializer, LostItemSerializer, 
    RegisterSerializer, UserSerializer, FoundItemStatusUpdateSerializer,
    LostItemStatusUpdateSerializer, NearestPickupPointSerializer
)
from .permissions import (
    IsAdmin, IsStaffOrPickupPoint, 
    CanManageFoundItem, CanManageLostItem)
from .models import Issuance
from .serializers import IssuanceSerializer, ConfirmIssuanceSerializer

# Регистрация
class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'user': UserSerializer(user).data,
                'message': 'Пользователь успешно создан'
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Категории
class CategoryListAPIView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

# Пункты выдачи
class PickupPointListAPIView(generics.ListAPIView):
    queryset = PickupPoint.objects.all()
    serializer_class = PickupPointSerializer
    permission_classes = [permissions.AllowAny]

# Находки
class FoundItemListCreateAPIView(generics.ListCreateAPIView):
    queryset = FoundItem.objects.all().order_by('-created_at')
    serializer_class = FoundItemSerializer
    pagination_class = PageNumberPagination
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    # Поля для точной фильтрации
    
    filterset_fields = {
    'status': ['exact'],
    'category': ['exact'],
    'pickup_point': ['exact'],
    'location_ref': ['icontains'],
    }
    
    
    # Поля для поиска
    search_fields = ['title', 'description']
    
    # Поля для сортировки
    ordering_fields = ['created_at', 'title', 'status']
    ordering = ['-created_at']  # Сортировка по умолчанию
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

class FoundItemRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    # Просмотр, обновление и удаление находки
    queryset = FoundItem.objects.all()
    serializer_class = FoundItemSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, CanManageFoundItem]
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), CanManageFoundItem()]
    
    def perform_update(self, serializer):
        serializer.save()
    
    def perform_destroy(self, instance):
        instance.delete()

# Пропажи
class LostItemListCreateAPIView(generics.ListCreateAPIView):
    queryset = LostItem.objects.all().order_by('-created_at')
    serializer_class = LostItemSerializer
    pagination_class = PageNumberPagination
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    
    # Поля для точной фильтрации
    filterset_fields = {
        'status': ['exact'],
        'category': ['exact'],
        'location_text': ['icontains'],
        'location_zone': ['icontains'],
    }
    
    # Поля для поиска
    search_fields = ['title', 'description']
    
    # Поля для сортировки
    ordering_fields = ['created_at', 'title', 'status']
    ordering = ['-created_at']
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context
    
    # def perform_create(self, serializer):
    #     lost_item = serializer.save(lost_by=self.request.user)
    
    #     # Поиск совпадений и отправка уведомлений
    #     from .views import MatchFoundItemsView
    #     match_view = MatchFoundItemsView()
    #     matches = find_matches(lost_item)
    def perform_create(self, serializer):
        lost_item = serializer.save(user=self.request.user)

        # ищем совпадения
        matches = find_matches(lost_item)

        # если есть совпадения → отправляем уведомление
        if matches:
            send_match_notification(lost_item, matches)

# if matches:
#     send_match_notification(lost_item, matches)

#         # Создаём имитацию запроса для поиска совпадений
#         # import json
#         # from django.test import RequestFactory
    
#         # factory = RequestFactory()
#         # mock_request = factory.get(f'/api/match/{lost_item.lost_id}/')
#         # mock_request.user = self.request.user
    
#         response = match_view.get(mock_request, lost_item_id=lost_item.lost_id)
    
#         if response.status_code == 200 and response.data.get('matches'):
#             send_match_notification(lost_item, response.data['matches'])

class LostItemRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    # Просмотр, обновление и удаление пропажи
    queryset = LostItem.objects.all()
    serializer_class = LostItemSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, CanManageLostItem]
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), CanManageLostItem()]
    
    def perform_update(self, serializer):
        serializer.save()
    
    def perform_destroy(self, instance):
        instance.delete()

# Найти похожие находки для указанной пропажи
class MatchFoundItemsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, lost_item_id):
        try:
            lost_item = LostItem.objects.get(id=lost_item_id)
        except LostItem.DoesNotExist:
            return Response({'error': 'Пропажа не найдена'}, status=404)
        
        # Базовый запрос: активные находки
        found_items = FoundItem.objects.filter(status='active')
        
        # Фильтр по категории (если указана)
        if lost_item.category:
            found_items = found_items.filter(category=lost_item.category)
        
        # Поиск по ключевым словам из заголовка и описания
        keywords = f"{lost_item.description}".split()
        for keyword in keywords[:10]:  # берём первые 10 слов
            if len(keyword) > 3:  # игнорируем короткие слова
                found_items = found_items.filter(
                    Q(description__icontains=keyword)
                )
        
        # Добавляем процент совпадения
        results = []
        for found in found_items[:20]:  # максимум 20 результатов
            score = self.calculate_match_score(lost_item, found)
            if score > 20:  # порог совпадения
                serializer = FoundItemSerializer(found)
                results.append({
                    'found_item': serializer.data,
                    'match_score': score
                })
        
        # Сортируем по убыванию совпадения
        results.sort(key=lambda x: x['match_score'], reverse=True)
        
        return Response({
            'lost_item_id': lost_item_id,
            'matches': results[:10]  # топ-10 совпадений
        })
    
def calculate_match_score(self, lost_item, found_item):
    score = 0

    # Совпадение категории
    if lost_item.category == found_item.category:
        score += 40

    # Совпадение описания
    lost_desc_words = set((lost_item.description or "").lower().split())
    found_desc_words = set((found_item.description or "").lower().split())

    common_desc = lost_desc_words & found_desc_words
    score += min(20, len(common_desc) * 2)

    # Совпадение местоположения
    lost_location = (lost_item.location_text or "").lower()
    found_location = (found_item.location_ref or "").lower()

    if (
        lost_location
        and found_location
        and (
            lost_location in found_location
            or found_location in lost_location
        )
    ):
        score += 20

    return min(100, score)

def send_match_notification(lost_item, found_items):
    """Отправляет email владельцу пропажи о найденных совпадениях"""

    if not lost_item.user.email:
        return

    matches_text = ""

    for item in found_items[:5]:
        matches_text += (
            f"\n- {item['found_item']['description'][:50]} "
            f"(совпадение: {item['match_score']}%)\n"
        )

        matches_text += (
            f"  Место: {item['found_item'].get('location_ref', 'Не указано')}\n"
        )

    subject = (
        f"Найдена похожая вещь: "
        f"{lost_item.category.name if lost_item.category else 'Предмет'}"
    )

    message = f"""
Здравствуйте, {lost_item.user.username}!

Мы нашли похожие вещи, которые могут быть вашей пропажей:

{matches_text}

Подробнее:
http://127.0.0.1:8000/api/lost/{lost_item.id}/

С уважением,
Команда UniFind
"""

    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [lost_item.user.email],
        fail_silently=False,
    )

class UpdateFoundItemStatusView(APIView):
    """Обновление статуса находки"""
    
    def get_permissions(self):
        if self.request.method == 'PATCH':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]
    
    def patch(self, request, pk):
        try:
            found_item = FoundItem.objects.get(pk=pk)
        except FoundItem.DoesNotExist:
            return Response({'error': 'Находка не найдена'}, status=404)
        
        # Проверка прав
        user = request.user
        is_admin = user.is_superuser or getattr(user, 'role', '') == 'admin'
        is_staff = getattr(user, 'role', '') == 'pickup_point'
        is_author = found_item.user == user
        
        if not (is_admin or is_staff or is_author):
            return Response(
                {'error': 'У вас нет прав для изменения статуса'},
                status=403
            )
        
        serializer = FoundItemStatusUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        
        new_status = serializer.validated_data['status']
        old_status = found_item.status
        
        found_item.status = new_status
        found_item.save()
        
        # Логирование изменения статуса
        from .utils import log_action
        log_action(
            user=user,
            action_type='status_change',
            entity_type='found_item',
            entity_id=found_item.id,
            action_data=f'Статус изменён с {old_status} на {new_status}',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return Response({
            'id': found_item.id,
            'status': found_item.status,
            'message': f'Статус изменён на {found_item.get_status_display()}'
        })


class UpdateLostItemStatusView(APIView):
    """Обновление статуса пропажи"""
    
    def get_permissions(self):
        if self.request.method == 'PATCH':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]
    
    def patch(self, request, pk):
        try:
            lost_item = LostItem.objects.get(pk=pk)
        except LostItem.DoesNotExist:
            return Response({'error': 'Пропажа не найдена'}, status=404)
        
        # Проверка прав
        user = request.user
        is_admin = user.is_superuser or getattr(user, 'role', '') == 'admin'
        is_author = lost_item.user == user
        
        if not (is_admin or is_author):
            return Response(
                {'error': 'У вас нет прав для изменения статуса'},
                status=403
            )
        
        serializer = LostItemStatusUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        
        new_status = serializer.validated_data['status']
        old_status = lost_item.status
        
        lost_item.status = new_status
        lost_item.save()
        
        # Логирование
        from .utils import log_action
        log_action(
            user=user,
            action_type='status_change',
            entity_type='lost_item',
            entity_id=lost_item.id,
            action_data=f'Статус изменён с {old_status} на {new_status}',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return Response({
            'id': lost_item.id,
            'status': lost_item.status,
            'message': f'Статус изменён на {lost_item.get_status_display()}'
        })
    
class AdminAllFoundItemsView(generics.ListAPIView):
    """Админ: просмотр всех находок"""
    serializer_class = FoundItemSerializer
    permission_classes = [IsAdmin]
    
    def get_queryset(self):
        queryset = FoundItem.objects.all().order_by('-created_at')
        
        # Фильтрация
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category_id=category)
        
        return queryset


class AdminAllLostItemsView(generics.ListAPIView):
    """Админ: просмотр всех пропаж"""
    serializer_class = LostItemSerializer
    permission_classes = [IsAdmin]
    
    def get_queryset(self):
        queryset = LostItem.objects.all().order_by('-created_at')
        
        # Фильтрация
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category_id=category)
        
        return queryset
    
class ConfirmIssuanceView(APIView):
    """Подтверждение выдачи вещи сотрудником пункта выдачи"""
    permission_classes = [IsStaffOrPickupPoint]
    
    def post(self, request):
        serializer = ConfirmIssuanceSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        
        found_item_id = serializer.validated_data['found_item_id']
        user_id = serializer.validated_data['user_id']
        verified_by = serializer.validated_data.get('verified_by', request.user.username)
        
        try:
            found_item = FoundItem.objects.get(id=found_item_id)
        except FoundItem.DoesNotExist:
            return Response({'error': 'Находка не найдена'}, status=404)
        
        # Проверка статуса находки
        if found_item.status != 'in_pickup':
            return Response(
                {'error': f'Вещь не может быть выдана. Текущий статус: {found_item.status}'},
                status=400
            )
        
        # Проверка, что находка принадлежит пункту выдачи сотрудника
        user_role = getattr(request.user, 'role', '')
        if user_role == 'pickup_point':
            # Сотрудник может выдавать только вещи своего пункта
            if found_item.pickup_point_id != getattr(request.user, 'pickup_point_id', None):
                return Response(
                    {'error': 'Вы можете выдавать только вещи вашего пункта выдачи'},
                    status=403
                )
        
        try:
            user_to_receive = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'Пользователь не найден'}, status=404)
        
        # Создаём запись о выдаче
        issuance = Issuance.objects.create(
            found_item=found_item,
            pickup_point=found_item.pickup_point,
            user=user_to_receive,
            verified_by=verified_by
        )
        
        # Меняем статус находки
        old_status = found_item.status
        found_item.status = 'issued'
        found_item.save()
        
        # Логирование
        from .utils import log_action
        log_action(
            user=request.user,
            action_type='issuance',
            entity_type='found_item',
            entity_id=found_item.id,
            action_data=f'Вещь выдана пользователю {user_to_receive.username}. Статус изменён с {old_status} на issued',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return Response({
            'message': 'Выдача успешно подтверждена',
            'issuance': IssuanceSerializer(issuance).data
        }, status=201)


class PickupPointItemsView(generics.ListAPIView):
    """Просмотр вещей, переданных в пункт выдачи сотрудника"""
    serializer_class = FoundItemSerializer
    permission_classes = [IsStaffOrPickupPoint]
    
    def get_queryset(self):
        user = self.request.user
        user_role = getattr(user, 'role', '')
        
        queryset = FoundItem.objects.filter(status__in=['active', 'in_pickup', 'has_match'])
        
        if user_role == 'pickup_point':
            # Сотрудник видит только вещи своего пункта
            pickup_point_id = getattr(user, 'pickup_point_id', None)
            if pickup_point_id:
                queryset = queryset.filter(pickup_point_id=pickup_point_id)
        
        return queryset.order_by('-created_at')


class PickupPointIssuanceHistoryView(generics.ListAPIView):
    """История выдач пункта выдачи"""
    serializer_class = IssuanceSerializer
    permission_classes = [IsStaffOrPickupPoint]
    
    def get_queryset(self):
        user = self.request.user
        user_role = getattr(user, 'role', '')
        
        if user_role == 'admin':
            return Issuance.objects.all().order_by('-issued_at')
        elif user_role == 'pickup_point':
            pickup_point_id = getattr(user, 'pickup_point_id', None)
            if pickup_point_id:
                return Issuance.objects.filter(pickup_point_id=pickup_point_id).order_by('-issued_at')
        
        return Issuance.objects.none()
    
class LogListView(generics.ListAPIView):
    """Просмотр логов (только для администратора)"""
    serializer_class = LogSerializer
    permission_classes = [IsAdmin]
    
    def get_queryset(self):
        queryset = Log.objects.all().order_by('-created_at')
        
        # Фильтрация
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        action_type = self.request.query_params.get('action_type')
        if action_type:
            queryset = queryset.filter(action_type=action_type)
        
        entity_type = self.request.query_params.get('entity_type')
        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)
        
        start_date = self.request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        
        end_date = self.request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)
        
        return queryset


class LogDetailView(generics.RetrieveAPIView):
    """Просмотр конкретного лога"""
    queryset = Log.objects.all()
    serializer_class = LogSerializer
    permission_classes = [IsAdmin]

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        serializer = UserSerializer(
            request.user,
            context={'request': request}
        )

        return Response(serializer.data)
        # return Response({
        #     "id": user.id,
        #     "email": user.email,
        #     "first_name": user.first_name,
        #     "username": user.username,
        #     "role": user.role if hasattr(user, "role") else None
        # })

    def patch(self, request):
        user = request.user

        serializer = UserSerializer(
            user,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(
            serializer.errors,
            status=400
        )    
class NearestPickupPointView(APIView):
    """
    Определяет ближайший пункт выдачи на основе геолокации пользователя
    Принимает POST запрос с координатами или GET запрос без параметров
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        """
        GET запрос (для клиентов, которые не хотят/не могут делиться геолокацией)
        Возвращает все пункты выдачи с сортировкой по умолчанию
        """
        pickup_points = PickupPoint.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False
        )
        serializer = PickupPointSerializer(pickup_points, many=True)
        return Response({
            'nearest': None,
            'message': 'Передайте координаты через POST запрос для определения ближайшего пункта',
            'all_points': serializer.data
        })
    
    def post(self, request):
        """
        POST запрос с координатами пользователя
        Пример тела запроса:
        {
            "latitude": 56.8383,
            "longitude": 60.6310
        }
        """
        serializer = NearestPickupPointSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        
        latitude = float(serializer.validated_data['latitude'])
        longitude = float(serializer.validated_data['longitude'])
        
        # Находим ближайший пункт
        nearest_point, distance = get_nearest_pickup_point(latitude, longitude)
        
        if not nearest_point or distance is None:
            return Response({
                "error": "Нет доступных пунктов выдачи"
            }, status=404)
        
        # Получаем все пункты с расстояниями (для дополнительной информации)
        all_points = []
        pickup_points = PickupPoint.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False
        )
        
        for point in pickup_points:
            point_distance = calculate_distance(
                latitude, longitude,
                float(point.latitude), float(point.longitude)
            )
            point_data = PickupPointSerializer(point).data
            point_data['distance_km'] = round(point_distance, 2)
            all_points.append(point_data)
        
        # Сортируем по расстоянию
        all_points.sort(key=lambda x: x['distance_km'])
        
        # Формируем ответ
        nearest_data = PickupPointSerializer(nearest_point).data
        nearest_data['distance_km'] = round(distance, 2)
        
        return Response({
            'nearest': nearest_data,
            'nearest_point_id': nearest_point.id,  # Удобно для автоматического выбора в форме
            'distance_km': round(distance, 2),
            'all_points': all_points,  # Все пункты с расстояниями
            'user_location': {
                'latitude': latitude,
                'longitude': longitude
            }
        })

class AutoSuggestPickupPointView(APIView):
    """
    Автоматически определяет пункт выдачи на основе геолокации
    Используется при создании объявления о находке
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = NearestPickupPointSerializer(data=request.data)
        
        if not serializer.is_valid():
            # Если координаты не переданы, возвращаем первый пункт
            first_point = PickupPoint.objects.first()
            return Response({
                'suggested': PickupPointSerializer(first_point).data if first_point else None,
                'message': 'Координаты не переданы. Показан пункт по умолчанию.',
                'user_location': None
            })
        
        latitude = float(serializer.validated_data['latitude'])
        longitude = float(serializer.validated_data['longitude'])
        
        nearest_point, distance = get_nearest_pickup_point(latitude, longitude)
        
        if nearest_point:
            return Response({
                'suggested': PickupPointSerializer(nearest_point).data,
                'suggested_id': nearest_point.id,
                'distance_km': round(distance, 2),
                'user_location': {
                    'latitude': latitude,
                    'longitude': longitude
                },
                'message': f'Ближайший пункт выдачи: {nearest_point.name} ({round(distance, 2)} км)'
            })
        
        return Response({
            'suggested': None,
            'error': 'Не удалось определить ближайший пункт'
        }, status=404)
    
class UploadAvatarView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        user = request.user

        file = request.FILES.get('avatar')

        if not file:
            return Response(
                {"error": "Файл не найден"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.avatar = file
        user.save()

        serializer = UserSerializer(
            user,
            context={'request': request}
        )

        return Response(serializer.data)

def send_push(token, title, body):
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        token=token,
    )

    messaging.send(message)


class MyItemsStatusView(APIView):
    """Получение статусов всех объявлений пользователя"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        found_items = FoundItem.objects.filter(user=request.user).order_by('-created_at')
        lost_items = LostItem.objects.filter(user=request.user).order_by('-created_at')
        
        result = []
        
        # Добавляем находки
        for item in found_items:
            result.append({
                'id': item.id,
                'title': item.title,
                'type': 'found',
                'type_display': 'Находка',
                'status': item.status,
                'status_display': item.get_status_display(),
                'category_name': item.category.name if item.category else None,
                'location': item.location,
                'created_at': item.created_at,
                'photo_url': item.image.url if item.image else None,
            })
        
        # Добавляем пропажи
        for item in lost_items:
            result.append({
                'id': item.id,
                'title': item.title,
                'type': 'lost',
                'type_display': 'Пропажа',
                'status': item.status,
                'status_display': item.get_status_display(),
                'category_name': item.category.name if item.category else None,
                'location': item.location,
                'created_at': item.created_at,
                'photo_url': item.photo.url if item.photo else None,
            })
        
        # Сортируем по дате создания (новые сверху)
        result.sort(key=lambda x: x['created_at'], reverse=True)
        
        # Статистика по статусам
        stats = {
            'total': len(result),
            'found_active': FoundItem.objects.filter(found_by=request.user, status='active').count(),
            'found_issued': FoundItem.objects.filter(found_by=request.user, status='issued').count(),
            'found_closed': FoundItem.objects.filter(found_by=request.user, status='closed').count(),
            'lost_active': LostItem.objects.filter(lost_by=request.user, status='active').count(),
            'lost_matched': LostItem.objects.filter(lost_by=request.user, status='matched').count(),
            'lost_closed': LostItem.objects.filter(lost_by=request.user, status='closed').count(),
        }
        
        return Response({
            'items': result,
            'stats': stats
        })


class MyFoundItemsView(generics.ListAPIView):
    """Мои находки"""
    serializer_class = FoundItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return FoundItem.objects.filter(found_by=self.request.user).order_by('-created_at')


class MyLostItemsView(generics.ListAPIView):
    """Мои пропажи"""
    serializer_class = LostItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return LostItem.objects.filter(lost_by=self.request.user).order_by('-created_at')
    
class AppealListView(generics.ListAPIView):
    """Просмотр обращений (свои для студента, все для админа)"""
    serializer_class = AppealSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or getattr(user, 'role', '') == 'admin':
            return Appeal.objects.all()
        return Appeal.objects.filter(user=user)


class AppealCreateView(generics.CreateAPIView):
    """Создание обращения"""
    serializer_class = AppealCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AppealDetailView(generics.RetrieveUpdateAPIView):
    """Просмотр и обновление обращения"""
    queryset = Appeal.objects.all()
    serializer_class = AppealSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        user = self.request.user
        is_admin = user.is_superuser or getattr(user, 'role', '') == 'admin'
        
        if self.request.method == 'PATCH' and is_admin:
            return AppealUpdateSerializer
        return AppealSerializer
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated()]
        return [IsAdmin()]