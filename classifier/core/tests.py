from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from core.models import User, WebCategory, UserAllowedCategory, BlockedDomain
import json
import warnings
from sklearn.exceptions import InconsistentVersionWarning

# Suppress scikit-learn version warnings
warnings.simplefilter("ignore", InconsistentVersionWarning)

class ClassifyAPITests(TransactionTestCase):
    reset_sequences = True  # Important for SQLite tests
    
    def setUp(self):
        # Clear any existing tokens and users first
        User.objects.all().delete()
        Token.objects.all().delete()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            device_id='550e8400-e29b-41d4-a716-446655440000'
        )
        
        # Create token - use get_or_create to be safe
        self.token, _ = Token.objects.get_or_create(user=self.user)
        
        # Create test categories
        self.allowed_category = WebCategory.objects.create(
            name='Education',
            description='Educational websites'
        )
        self.blocked_category = WebCategory.objects.create(
            name='Games',
            description='Gaming websites'
        )
        
        # Allow education category for user
        UserAllowedCategory.objects.create(
            user=self.user,
            category=self.allowed_category
        )
        
        # Set up API client with token auth
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        self.classify_url = reverse('classify')
    
    def _parse_response(self, response):
        """Helper to parse JsonResponse content"""
        return json.loads(response.content.decode('utf-8'))
    
    def test_classify_allowed_website(self):
        """Test classification of allowed website"""
        response = self.client.post(
            self.classify_url,
            data={
                'domain': 'example.edu',
                'text_content': 'Educational content',
                'user_id': self.user.id
            },
            format='json'
        )
        
        data = self._parse_response(response)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(data['block'])
        self.assertEqual(data['category'], 'Education')
    
    def test_classify_blocked_website(self):
        """Test classification of blocked website"""
        response = self.client.post(
            self.classify_url,
            data={
                'domain': 'game-site.com',
                'text_content': 'Gaming content',
                'user_id': self.user.id
            },
            format='json'
        )
        
        data = self._parse_response(response)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(data['block'])
        self.assertEqual(data['category'], 'Games')
        self.assertTrue(BlockedDomain.objects.filter(domain='game-site.com').exists())
    
    def test_classify_previously_blocked_domain(self):
        """Test that previously blocked domains are immediately blocked"""
        # First request to block the domain
        self.client.post(
            self.classify_url,
            data={
                'domain': 'game-site.com',
                'text_content': 'Gaming content',
                'user_id': self.user.id
            },
            format='json'
        )
        
        # Second request
        response = self.client.post(
            self.classify_url,
            data={
                'domain': 'game-site.com',
                'text_content': 'Different content',
                'user_id': self.user.id
            },
            format='json'
        )
        
        data = self._parse_response(response)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(data['block'])
        self.assertEqual(data.get('reason'), 'domain_blocked')
    
    def test_classify_missing_parameters(self):
        """Test classification with missing required parameters"""
        test_cases = [
            {'domain': 'example.com'},  # Missing text_content
            {'text_content': 'some content'},  # Missing domain
            {'domain': 'example.com', 'text_content': 'content'}  # Missing user_id
        ]
        
        for data in test_cases:
            response = self.client.post(
                self.classify_url,
                data=data,
                format='json'
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_classify_unauthenticated(self):
        """Test that unauthenticated requests are rejected"""
        client = APIClient()  # No authentication
        response = client.post(
            self.classify_url,
            data={
                'domain': 'example.com',
                'text_content': 'content',
                'user_id': 1
            },
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)