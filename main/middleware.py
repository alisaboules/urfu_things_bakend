from .utils import log_action, get_client_ip

class LoggingMiddleware:
    """Middleware для логирования всех действий"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Логируем только POST, PUT, PATCH, DELETE запросы
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            user = request.user if request.user.is_authenticated else None
            if user:
                log_action(
                    user=user,
                    action_type=request.method.lower(),
                    entity_type=request.path.split('/')[1] if len(request.path.split('/')) > 1 else 'unknown',
                    entity_id=0,  # ID будет определён позже
                    action_data={
                        'path': request.path,
                        'data': str(request.body)[:500]  # Ограничиваем размер
                    },
                    ip_address=get_client_ip(request)
                )
        
        return response