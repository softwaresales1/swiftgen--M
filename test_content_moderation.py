#!/usr/bin/env python
"""
Test script for content moderation system
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

def test_contact_detection():
    """Test various contact information patterns"""
    
    # Test messages that should be blocked
    test_messages = [
        "Contact me at john@gmail.com",
        "My email is john dot smith at gmail dot com",
        "Call me at 555-123-4567",
        "Text me on WhatsApp: +1 555 123 4567",
        "Find me on Instagram @johnsmith",
        "Check out my portfolio at johnsmith.com",
        "Visit my website: https://johnsmith.dev",
        "My LinkedIn is linkedin.com/in/johnsmith",
        "Follow me on Twitter @john_smith",
        "Add me on Discord: johnsmith#1234",
        "My phone number is five five five one two three four five six seven",
        "google me: john smith portfolio",
        "search for me on behance",
        "check my dribbble profile",
        "my github is github.com/johnsmith",
        "bit.ly/johnportfolio",
        "Contact me outside this platform",
        "Let's move to WhatsApp",
        "john(at)gmail(dot)com",
        "555[dash]123[dash]4567"
    ]
    
    # Test messages that should be allowed
    safe_messages = [
        "Hello, how are you?",
        "I can help you with your project",
        "What's your budget for this work?",
        "When do you need this completed?",
        "I have experience in web development",
        "Can you share more details about the project?",
        "I'm available to start immediately",
        "My rate is $50 per hour"
    ]
    
    print("🛡️ Testing Content Moderation System")
    print("=" * 50)
    
    # Create a test user
    try:
        test_user = User.objects.get(username='testuser')
    except User.DoesNotExist:
        test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    print("\n🚫 Testing messages that SHOULD be blocked:")
    print("-" * 40)
    
    blocked_count = 0
    for i, message in enumerate(test_messages, 1):
        result = content_moderator.moderate_message(test_user, message)
        status = "🚫 BLOCKED" if not result['allowed'] else "✅ ALLOWED"
        print(f"{i:2d}. {status} - {message[:50]}...")
        if not result['allowed']:
            blocked_count += 1
            print(f"    Action: {result['action']}")
            print(f"    Detected: {list(result.get('detected_content', {}).keys())}")
        print()
    
    print(f"\nBlocked {blocked_count}/{len(test_messages)} suspicious messages")
    
    print("\n✅ Testing messages that SHOULD be allowed:")
    print("-" * 40)
    
    allowed_count = 0
    for i, message in enumerate(safe_messages, 1):
        result = content_moderator.moderate_message(test_user, message)
        status = "✅ ALLOWED" if result['allowed'] else "🚫 BLOCKED"
        print(f"{i:2d}. {status} - {message}")
        if result['allowed']:
            allowed_count += 1
        elif not result['allowed']:
            print(f"    FALSE POSITIVE! Detected: {list(result.get('detected_content', {}).keys())}")
        print()
    
    print(f"\nAllowed {allowed_count}/{len(safe_messages)} safe messages")
    
    # Test violation tracking
    print("\n📊 Testing violation tracking:")
    print("-" * 40)
    
    # Trigger multiple violations
    violation_messages = [
        "Email me at test@gmail.com",
        "My phone is 555-123-4567", 
        "Find me on Instagram @test"
    ]
    
    for i, message in enumerate(violation_messages, 1):
        result = content_moderator.moderate_message(test_user, message)
        print(f"Violation {i}: {result['action']} - {result['message']}")
    
    print("\n🔍 Summary:")
    print(f"Content moderation system is {'✅ WORKING' if blocked_count > len(test_messages) * 0.8 else '❌ NOT WORKING PROPERLY'}")

if __name__ == "__main__":
    test_contact_detection()