from django.urls import path
from . import views

urlpatterns = [
    # Регистрация
    path('register/', views.RegisterView.as_view(), name='register'),
    path('me/', views.MeView.as_view(), name='me'),

    
    # Категории и пункты выдачи
    path('categories/', views.CategoryListAPIView.as_view(), name='categories'),
    path('pickup-points/', views.PickupPointListAPIView.as_view(), name='pickup-points'),
    
    # Находки
    path('found/', views.FoundItemListCreateAPIView.as_view(), name='found-list'),
    path('found/<int:pk>/', views.FoundItemRetrieveUpdateDestroyAPIView.as_view(), name='found-detail'),
    
    # Пропажи
    path('lost/', views.LostItemListCreateAPIView.as_view(), name='lost-list'),
    path('lost/<int:pk>/', views.LostItemRetrieveUpdateDestroyAPIView.as_view(), name='lost-detail'),
    
    # Сопоставление
    path('match/<int:lost_item_id>/', views.MatchFoundItemsView.as_view(), name='match'),

    # Статусы находок
    path('found/<int:pk>/update-status/', views.UpdateFoundItemStatusView.as_view(), name='update-found-status'),
    
    # Статусы пропаж
    path('lost/<int:pk>/update-status/', views.UpdateLostItemStatusView.as_view(), name='update-lost-status'),

    # Админские маршруты
    path('admin/found/', views.AdminAllFoundItemsView.as_view(), name='admin-found'),
    path('admin/lost/', views.AdminAllLostItemsView.as_view(), name='admin-lost'),

    # Выдача вещей
    path('issuance/confirm/', views.ConfirmIssuanceView.as_view(), name='confirm-issuance'),
    path('pickup-point/items/', views.PickupPointItemsView.as_view(), name='pickup-point-items'),
    path('pickup-point/history/', views.PickupPointIssuanceHistoryView.as_view(), name='pickup-point-history'),

    # Логи
    path('logs/', views.LogListView.as_view(), name='log-list'),
    path('logs/<int:pk>/', views.LogDetailView.as_view(), name='log-detail'),
]