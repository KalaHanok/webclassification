from django.urls import path
from . import views

urlpatterns = [
    path('api/classify/', views.classify_website, name='classify'),
    path('api/register/', views.RegisterAPIView.as_view(), name='api_register'),
    path('api/get-device-id/', views.GetDeviceIDAPIView.as_view(), name='get_device_id'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('manage-categories/', views.manage_categories, name='manage_categories'),
    path('register/', views.register, name='register'),
    path('accounts/login/', views.login_view, name='login'),
    path('accounts/logout/', views.logout_view, name='logout'),
    

]