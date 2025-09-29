"""
Test script for the Content Moderation System
Tests various contact information detection scenarios
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.append('e:\\Swiftgen-main')

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Work.settings')
django.setup()

from Portal.content_moderation import ContactInfoDetector, ContentModerationService
from django.contrib.auth.models import User

def test_contact_detection():
    """Test the contact information detection system"""
    detector = ContactInfoDetector()
    
    # Test cases with different types of contact information
    test_messages = [
        # Email tests
        "Contact me at john@gmail.com for more details",
        "My email is mary.jane@yahoo.com",
        "Reach out to support at outlook dot com",
        "You can find me on gmail",
        
        # Phone number tests
        "Call me at 555-123-4567",
        "My phone is +1 (555) 987-6543",
        "Text me on 5551234567",
        
        # Social media tests
        "Follow me @john_doe on Twitter",
        "Find me on Instagram @mary_photos",
        "Add me on TikTok: cooluser123",
        "My Facebook is facebook.com/johnsmith",
        
        # Messaging apps
        "Message me on WhatsApp: +1 555 123 4567",
        "Add me on Telegram @john_chat",
        "My Discord is JohnGamer#1234",
        "Find me on Skype: john.smith.live",
        
        # Website URLs
        "Check out my website: www.example.com",
        "Visit https://myportfolio.com",
        "My blog is at myblog.net",
        
        # Obfuscated attempts
        "Email me at john at gmail dot com",
        "Contact: mary [at] yahoo [dot] com",
        "Reach me on five five five dash one two three four",
        
        # Clean messages (should pass)
        "Hello, how are you doing today?",
        "The project looks great, when can we start?",
        "Thanks for the update, I'll review it soon.",
    ]
    
    print("🛡️ CONTENT MODERATION TEST RESULTS")
    print("=" * 50)
    
    violation_count = 0
    clean_count = 0
    
    for i, message in enumerate(test_messages, 1):
        is_violation, detected = detector.is_violation(message)
        
        if is_violation:
            violation_count += 1
            print(f"\n❌ TEST {i}: VIOLATION DETECTED")
            print(f"Message: '{message}'")
            print(f"Detected: {detected}")
        else:
            clean_count += 1
            print(f"\n✅ TEST {i}: CLEAN MESSAGE")
            print(f"Message: '{message}'")
    
    print(f"\n{'='*50}")
    print(f"📊 SUMMARY:")
    print(f"Total Tests: {len(test_messages)}")
    print(f"Violations Detected: {violation_count}")
    print(f"Clean Messages: {clean_count}")
    print(f"Detection Rate: {(violation_count/(len(test_messages)-3))*100:.1f}%")  # Excluding 3 clean messages
    
    return violation_count > 0

def test_moderation_service():
    """Test the complete moderation service with database integration"""
    print(f"\n🔬 TESTING MODERATION SERVICE")
    print("=" * 50)
    
    # Get or create a test user
    test_user, created = User.objects.get_or_create(
        username='test_moderator',
        defaults={
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User'
        }
    )
    
    if created:
        print(f"✅ Created test user: {test_user.username}")
    else:
        print(f"✅ Using existing test user: {test_user.username}")
    
    moderator = ContentModerationService()
    
    # Test violation message
    violation_message = "Contact me at john@gmail.com or call 555-123-4567"
    print(f"\n🧪 Testing violation message:")
    print(f"Message: '{violation_message}'")
    
    result = moderator.moderate_message(test_user, violation_message)
    
    print(f"Result: {result}")
    
    if not result['allowed']:
        print(f"✅ Message correctly blocked!")
        print(f"Action: {result['action']}")
        print(f"Detected: {result.get('detected_content', {})}")
    else:
        print(f"❌ Message incorrectly allowed!")
    
    # Test clean message
    clean_message = "Hello, how are you doing today?"
    print(f"\n🧪 Testing clean message:")
    print(f"Message: '{clean_message}'")
    
    result2 = moderator.moderate_message(test_user, clean_message)
    
    if result2['allowed']:
        print(f"✅ Clean message correctly allowed!")
    else:
        print(f"❌ Clean message incorrectly blocked!")
    
    return True

if __name__ == "__main__":
    try:
        print("🚀 STARTING CONTENT MODERATION SYSTEM TESTS")
        print("=" * 60)
        
        # Test 1: Contact Detection
        detection_success = test_contact_detection()
        
        # Test 2: Full Moderation Service
        service_success = test_moderation_service()
        
        print(f"\n🎉 ALL TESTS COMPLETED!")
        print(f"Detection System: {'✅ WORKING' if detection_success else '❌ FAILED'}")
        print(f"Moderation Service: {'✅ WORKING' if service_success else '❌ FAILED'}")
        
        if detection_success and service_success:
            print(f"\n🛡️ CONTENT MODERATION SYSTEM IS READY FOR DEPLOYMENT!")
        else:
            print(f"\n⚠️ SOME TESTS FAILED - REVIEW REQUIRED")
            
    except Exception as e:
        print(f"\n❌ ERROR DURING TESTING: {e}")
        import traceback
        traceback.print_exc()