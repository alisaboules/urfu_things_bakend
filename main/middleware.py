from .utils import log_action, get_client_ip

# class LoggingMiddleware:
#     """Middleware для логирования всех действий"""
    
#     def __init__(self, get_response):
#         self.get_response = get_response
    
#     def __call__(self, request):
#         response = self.get_response(request)
        
#         # Логируем только POST, PUT, PATCH, DELETE запросы
#         if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
#             user = request.user if request.user.is_authenticated else None
#             if user:
#                 log_action(
#                     user=user,
#                     action_type=request.method.lower(),
#                     entity_type=request.path.split('/')[1] if len(request.path.split('/')) > 1 else 'unknown',
#                     entity_id=0,  # ID будет определён позже
#                     action_data={
#                         'path': request.path,
#                         'data': str(request.body)[:500]  # Ограничиваем размер
#                     },
#                     ip_address=get_client_ip(request)
#                 )
        
#         return response

from django.utils.deprecation import MiddlewareMixin
import json

class LoggingMiddleware(MiddlewareMixin):

    def process_response(self, request, response):

        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:

            user = getattr(request, "user", None)
            if user and user.is_authenticated:

                # ВАЖНО: НЕ request.body
                data = getattr(request, "data", None)

                try:
                    safe_data = dict(data) if data else None
                except Exception:
                    safe_data = str(data) if data else None

                log_action(
                    user=user,
                    action_type=request.method.lower(),
                    entity_type=request.path.split('/')[1] if len(request.path.split('/')) > 1 else 'unknown',
                    entity_id=0,
                    action_data={
                        "path": request.path,
                        "data": safe_data
                    },
                    ip_address=get_client_ip(request)
                )

        return response
