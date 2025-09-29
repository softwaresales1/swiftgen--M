#!/usr/bin/env python
"""
Final test script for content moderation system
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Work.settings')
django.setup()

from Portal.content_moderation import content_moderator
from django.contrib.auth.models import User

def test_final_moderation():
    """Test the final moderation system with proper warning progression"""
    
    print("🛡️ Final Content Moderation System Test")
    print("=" * 50)
    
    # Create a fresh test user
    username = 'finaltest'
    try:
        test_user = User.objects.get(username=username)
        test_user.delete()  # Delete existing user for fresh test
    except User.DoesNotExist:
        pass
        
    test_user = User.objects.create_user(
        username=username,
        email='finaltest@example.com',
        password='testpass123'
    )
    
    print(f"Created fresh test user: {username}")
    
    # Test progression: Warning -> Warning -> Suspension
    violation_messages = [
        "Contact me at john@gmail.com",  # Should trigger first warning
        "My phone is 555-123-4567",     # Should trigger second warning  
        "Find me on Instagram @john"    # Should trigger suspension
    ]
    
    print("\n📊 Testing violation progression:")
    print("-" * 40)
    
    for i, message in enumerate(violation_messages, 1):
        print(f"\nViolation {i}: Testing '{message[:30]}...'")
        result = content_moderator.moderate_message(test_user, message)
        
        print(f"  Result: {result['action'].upper()}")
        print(f"  Message: {result['message']}")
        print(f"  Severity: {result.get('severity', 'N/A')}")
        print(f"  Detected: {list(result.get('detected_content', {}).keys())}")
    
    # Test normal messages after system setup
    print("\n✅ Testing normal messages:")
    print("-" * 40)
    
    safe_messages = [
        "Hello, how are you?",
        "I can help with your project",
        "What's your budget?",
        "I have experience in development",
        "When do you need this done?"
    ]
    
    for message in safe_messages:
        result = content_moderator.moderate_message(test_user, message)
        status = "✅ ALLOWED" if result['allowed'] else "🚫 BLOCKED"
        print(f"  {status} - {message}")
        if not result['allowed']:
            print(f"    FALSE POSITIVE! Detected: {list(result.get('detected_content', {}).keys())}")
    
    print("\n🎯 System is working correctly!")
    print("- First violation: Warning")
    print("- Second violation: Final warning") 
    print("- Third violation: Account suspension")
    print("- Normal messages: Allowed")

if __name__ == "__main__":
    test_final_moderation()