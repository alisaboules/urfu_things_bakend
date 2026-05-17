from .models import Log
import json
from .models import FoundItem
from .models import PickupPoint
from .serializers import FoundItemSerializer
from math import radians, sin, cos, sqrt, atan2
# from .views import calculate_match_score

def log_action(user, action_type, entity_type, entity_id, action_data=None, ip_address=None):
    """Запись действия в лог"""
    if not user or not user.is_authenticated:
        return
    
    # Преобразуем action_data в строку, если это словарь
    if isinstance(action_data, dict):
        action_data = json.dumps(action_data, ensure_ascii=False)
    
    Log.objects.create(
        user=user,
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        action_data=action_data,
        ip_address=ip_address
    )


def get_client_ip(request):
    """Получение IP адреса клиента"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def find_matches(lost_item):
    found_items = FoundItem.objects.filter(status='active')

    if lost_item.category:
        found_items = found_items.filter(category=lost_item.category)

    results = []
    for found in found_items:
        score = calculate_match_score(lost_item, found)
        if score > 20:
            results.append({
                "found_item": FoundItemSerializer(found).data,
                "match_score": score
            })

    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results
def calculate_match_score(lost_item, found_item):
    score = 0

    if lost_item.category == found_item.category:
        score += 40

    lost_title_words = set(lost_item.title.lower().split())
    found_title_words = set(found_item.title.lower().split())
    common_title = lost_title_words & found_title_words
    score += min(20, len(common_title) * 5)

    lost_desc_words = set(lost_item.description.lower().split())
    found_desc_words = set(found_item.description.lower().split())
    common_desc = lost_desc_words & found_desc_words
    score += min(20, len(common_desc) * 2)

    lost_location = lost_item.location.lower()
    found_location = found_item.location.lower()
    if lost_location in found_location or found_location in lost_location:
        score += 20

    return min(100, score)


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Рассчитывает расстояние между двумя точками на Земле (в километрах)
    Используется формула гаверсинуса
    """
    R = 6371  # Радиус Земли в километрах
    
    lat1_rad = radians(lat1)
    lon1_rad = radians(lon1)
    lat2_rad = radians(lat2)
    lon2_rad = radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    distance = R * c
    return distance


def get_nearest_pickup_point(latitude, longitude):
    """
    Находит ближайший пункт выдачи к заданным координатам
    """
    pickup_points = PickupPoint.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False
    )
    
    if not pickup_points.exists():
        return None
    
    nearest_point = None
    min_distance = float('inf')
    
    for point in pickup_points:
        distance = calculate_distance(
            latitude, longitude,
            float(point.latitude), float(point.longitude)
        )
        
        if distance < min_distance:
            min_distance = distance
            nearest_point = point
    
    return nearest_point, min_distance