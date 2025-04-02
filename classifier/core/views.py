from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from .models import User, UserAllowedCategory, BlockedDomain, WebCategory
from ml_model.classifier import classifier
import tldextract
import json
import logging
import uuid
from .forms import CustomUserCreationForm
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import UserRegistrationSerializer
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate
from rest_framework import serializers

logger = logging.getLogger(__name__)




def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'core/register.html', {'form': form})

class RegisterAPIView(APIView):
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)  # Auto returns 400 if invalid
        
        try:
            user = serializer.save()
            return Response({
                'user_id': user.id,
                'device_id': user.device_id,
                'username': user.username
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class AuthSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True)

class GetDeviceIDAPIView(APIView):
    def post(self, request):
        serializer = AuthSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user = authenticate(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password']
        )
        
        if not user:
            return Response(
                {'error': 'Invalid credentials'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
            
        if not hasattr(user, 'device_id'):
            return Response(
                {'error': 'Device ID not found for user'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        return Response({
            'device_id': user.device_id,
            'user_id': user.id
        })

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            
            # Verify device if required
            if user.requires_device_auth:
                device_hash = request.POST.get('device_hash')
                if not device_hash or device_hash != user.hashed_mac:
                    logger.warning(
                        f"Device verification failed for {user.username}",
                        extra={'request': request}
                    )
                    return render(request, 'core/login.html', {
                        'form': form,
                        'error': 'Device verification failed'
                    })
            
            auth_login(request, user)
            user.update_device_metadata(request)
            return redirect('dashboard')
    else:
        form = AuthenticationForm()
    
    return render(request, 'core/login.html', {'form': form})

def logout_view(request):
    auth_logout(request)
    return redirect('login')

# Main Application Views
@login_required
def dashboard(request):
    allowed_categories = UserAllowedCategory.objects.filter(user=request.user)
    blocked_domains = BlockedDomain.objects.filter(user=request.user).order_by('-blocked_at')
    all_categories = WebCategory.objects.all()
    
    context = {
        'allowed_categories': allowed_categories,
        'blocked_domains': blocked_domains,
        'all_categories': all_categories,
        'uuid': request.user.uuid,
        'requires_device_auth': request.user.requires_device_auth
    }
    return render(request, 'core/dashboard.html', context)

@login_required
def manage_categories(request):
    if request.method == 'POST':
        category_id = request.POST.get('category_id')
        action = request.POST.get('action')
        
        if action == 'add':
            try:
                category = WebCategory.objects.get(id=category_id)
                UserAllowedCategory.objects.get_or_create(
                    user=request.user,
                    category=category
                )
            except ObjectDoesNotExist:
                logger.error(f"Category {category_id} not found")
        elif action == 'remove':
            UserAllowedCategory.objects.filter(
                user=request.user,
                category_id=category_id
            ).delete()
    
    return redirect('dashboard')

@login_required
def unblock_domain(request, domain_id):
    if request.method == 'POST':
        try:
            blocked_domain = BlockedDomain.objects.get(
                id=domain_id,
                user=request.user
            )
            blocked_domain.delete()
        except ObjectDoesNotExist:
            logger.error(f"Blocked domain {domain_id} not found for user {request.user.id}")
    return redirect('dashboard')

# API Views
@csrf_exempt
def classify_website(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            domain = data.get('domain')
            text_content = data.get('text_content')
            device_id = data.get('device_id')
            
            if not all([domain, text_content, device_id]):
                return JsonResponse(
                    {'error': 'Missing required parameters'},
                    status=400
                )
            user = User.objects.get(device_id=device_id)
            user_id = user.id
            # Extract main domain (e.g., www.google.com → google.com)
            extracted = tldextract.extract(domain)
            main_domain = f"{extracted.domain}.{extracted.suffix}"
            
            # Check if domain is already blocked
            if BlockedDomain.objects.filter(
                user_id=user_id,
                domain__icontains=main_domain
            ).exists():
                return JsonResponse({
                    'block': True,
                    'reason': 'domain_blocked',
                    'domain': main_domain
                })
            
            # Get user's allowed categories
            allowed_categories = set(
                UserAllowedCategory.objects.filter(user_id=user_id)
                .values_list('category__name', flat=True)
            )
            
            # Classify the content
            classification_result = classifier.predict(text_content)
            
            if 'error' in classification_result:
                logger.error(f"Classification failed: {classification_result['error']}")
                return JsonResponse({
                    'error': 'classification_failed',
                    'details': classification_result['error']
                }, status=500)
            
            category = classification_result['category']
            confidence = classification_result.get('confidence', 0)
            
            # Create category if it doesn't exist
            web_category, _ = WebCategory.objects.get_or_create(
                name=category,
                defaults={'description': f'Automatically created category: {category}'}
            )
            
            # Decision to block
            if category not in allowed_categories:
                BlockedDomain.objects.create(
                    user_id=user_id,
                    domain=main_domain,
                    original_category=web_category
                )
                return JsonResponse({
                    'block': True,
                    'category': category,
                    'confidence': confidence,
                    'domain': main_domain
                })
            
            return JsonResponse({
                'block': False,
                'category': category,
                'confidence': confidence,
                'domain': main_domain
            })
            
        except json.JSONDecodeError:
            return JsonResponse(
                {'error': 'Invalid JSON payload'},
                status=400
            )
        except Exception as e:
            logger.error(f"Classification error: {str(e)}", exc_info=True)
            return JsonResponse(
                {'error': 'internal_server_error'},
                status=500
            )
    
    return JsonResponse(
        {'error': 'method_not_allowed'},
        status=405
    )