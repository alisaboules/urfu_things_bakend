from rest_framework import permissions

class IsAdmin(permissions.BasePermission):
    """Проверка, является ли пользователь администратором"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            request.user.is_superuser or 
            getattr(request.user, 'role', '') == 'admin'
        )
    
    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsStaffOrPickupPoint(permissions.BasePermission):
    """Проверка, является ли пользователь сотрудником пункта выдачи"""
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            request.user.is_superuser or 
            getattr(request.user, 'role', '') in ['admin', 'pickup_point']
        )


class CanManageFoundItem(permissions.BasePermission):
    """Проверка прав на управление находкой"""
    def has_object_permission(self, request, view, obj):
        user = request.user
        # Админ может всё
        if user.is_superuser or getattr(user, 'role', '') == 'admin':
            return True
        # Автор может редактировать свою находку
        if hasattr(obj, 'found_by') and obj.found_by == user:
            return True
        if hasattr(obj, 'user') and obj.user == user:
            return True
        return False


class CanManageLostItem(permissions.BasePermission):
    """Проверка прав на управление пропажей"""
    def has_object_permission(self, request, view, obj):
        user = request.user
        # Админ может всё
        if user.is_superuser or getattr(user, 'role', '') == 'admin':
            return True
        # Автор может редактировать свою пропажу
        if hasattr(obj, 'lost_by') and obj.lost_by == user:
            return True
        if hasattr(obj, 'user') and obj.user == user:
            return True
        return False