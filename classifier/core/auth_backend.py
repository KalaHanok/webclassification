from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import PermissionDenied
from .models import User
import logging

logger = logging.getLogger(__name__)

class DeviceAwareAuthBackend(ModelBackend):
    """Authentication backend with device verification"""
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        # Standard password authentication
        user = super().authenticate(request, username, password)
        if not user:
            return None
            
        # Device verification
        device_hash = kwargs.get('device_hash')
        if user.requires_device_auth:
            if not device_hash or device_hash != user.hashed_mac:
                logger.warning(
                    f"Device verification failed for user {user.username}",
                    extra={'request': request}
                )
                raise PermissionDenied("Device verification failed")
                
        # Update device metadata
        if request:
            user.update_device_metadata(request)
            
        return user