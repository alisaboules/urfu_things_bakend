from .models import Log
import json
from .models import FoundItem
from .serializers import FoundItemSerializer
from .views import calculate_match_score

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
