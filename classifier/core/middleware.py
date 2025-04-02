from django.utils.deprecation import MiddlewareMixin
from django.core.exceptions import PermissionDenied
from rest_framework.authtoken.models import Token
import logging

logger = logging.getLogger(__name__)

class DeviceVerificationMiddleware(MiddlewareMixin):
    """Middleware for API device verification"""
    
    def process_request(self, request):
        # Skip for non-API paths
        if not request.path.startswith('/api/'):
            return
            
        # Skip for authentication endpoints
        if request.path in ['/api/login/', '/api/register/']:
            return
            
        # Verify device for authenticated API requests
        if request.user.is_authenticated and request.user.requires_device_auth:
            device_hash = request.META.get('HTTP_X_DEVICE_HASH')
            if not device_hash or device_hash != request.user.hashed_mac:
                logger.warning(
                    f"API device verification failed for {request.user.username}",
                    extra={'request': request}
                )
                raise PermissionDenied("Device verification failed")