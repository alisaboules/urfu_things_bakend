from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from .models import Category, Log, PickupPoint, FoundItem, LostItem, User
from django.db.models import Q
from django.core.mail import send_mail
from django.conf import settings
from .utils import find_matches
from rest_framework.pagination import PageNumberPagination
from .serializers import (
    CategorySerializer, LogSerializer, PickupPointSerializer, 
    FoundItemSerializer, LostItemSerializer, 
    RegisterSerializer, UserSerializer, FoundItemStatusUpdateSerializer,
    LostItemStatusUpdateSerializer
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
        lost_item = serializer.save(lost_by=self.request.user)

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
        keywords = f"{lost_item.title} {lost_item.description}".split()
        for keyword in keywords[:10]:  # берём первые 10 слов
            if len(keyword) > 3:  # игнорируем короткие слова
                found_items = found_items.filter(
                    Q(title__icontains=keyword) | Q(description__icontains=keyword)
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
        # Рассчитывает процент совпадения между пропажей и находкой
        score = 0
        
        # Совпадение категории (40 баллов)
        if lost_item.category == found_item.category:
            score += 40
        
        # Совпадение в заголовке (20 баллов)
        lost_title_words = set(lost_item.title.lower().split())
        found_title_words = set(found_item.title.lower().split())
        common_title = lost_title_words & found_title_words
        score += min(20, len(common_title) * 5)
        
        # Совпадение в описании (20 баллов)
        lost_desc_words = set(lost_item.description.lower().split())
        found_desc_words = set(found_item.description.lower().split())
        common_desc = lost_desc_words & found_desc_words
        score += min(20, len(common_desc) * 2)
        
        # Бонус за совпадение местоположения (20 баллов)
        lost_location = lost_item.location.lower()
        found_location = found_item.location.lower()
        if lost_location in found_location or found_location in lost_location:
            score += 20
        
        return min(100, score)  # максимум 100%
    
def send_match_notification(lost_item, found_items):
    """Отправляет email владельцу пропажи о найденных совпадениях"""
    if not lost_item.lost_by.email:
        return
    
    matches_text = ""
    for item in found_items[:5]:
        matches_text += f"\n- {item['found_item']['title']} (совпадение: {item['match_score']}%)\n"
        matches_text += f"  Место: {item['found_item']['location']}\n"
    
    subject = f"Найдена похожая вещь: {lost_item.title}"
    message = f"""
Здравствуйте, {lost_item.lost_by.username}!

Мы нашли похожие вещи, которые могут быть вашей пропажей:

{matches_text}

Пожалуйста, войдите в систему для получения более подробной информации:
http://127.0.0.1:8000/api/lost/{lost_item.lost_id}/

С уважением,
Команда UniFind
"""
    
    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [lost_item.lost_by.email],
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
        user = request.user

        return Response({
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "username": user.username,
            "role": user.role if hasattr(user, "role") else None
        })