"""
Content Moderation System for Contact Information Detection
Detects and prevents sharing of contact information in messages
"""
import re
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


class ContactInfoDetector:
    """
    Advanced contact information detection system with zero tolerance policy
    """
    
    def __init__(self):
        self.patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """
        Compile comprehensive regex patterns for contact information detection
        """
        patterns = {
            'email': [
                # Standard email patterns
                re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', re.IGNORECASE),
                # Obfuscated emails (gmail dot com, @ replaced with at, etc.)
                re.compile(r'\b[A-Za-z0-9._%+-]+\s*(at|@|\[at\])\s*[A-Za-z0-9.-]+\s*(dot|\.)\s*[A-Z|a-z]{2,}\b', re.IGNORECASE),
                # Popular email domains mentioned
                re.compile(r'\b[A-Za-z0-9._%+-]+\s*(gmail|yahoo|outlook|hotmail|protonmail|icloud)\b', re.IGNORECASE),
                # Email with spaces or special chars
                re.compile(r'\b[A-Za-z0-9._%+-]+\s+[A-Za-z0-9.-]+\s+[A-Z|a-z]{2,}\b', re.IGNORECASE),
            ],
            
            'phone': [
                # US phone numbers (various formats)
                re.compile(r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b'),
                # International phone numbers
                re.compile(r'\b\+?[1-9]\d{1,14}\b'),
                # Phone with text
                re.compile(r'\b(phone|call|text|mobile|cell|number)[\s:]*[\+]?[0-9\s\-\.\(\)]{10,15}\b', re.IGNORECASE),
                # Obfuscated phone numbers
                re.compile(r'\b[0-9]{3}[\s\-\.]*[0-9]{3}[\s\-\.]*[0-9]{4}\b'),
            ],
            
            'social_media': [
                # Twitter/X handles
                re.compile(r'@[A-Za-z0-9_]{1,15}\b'),
                re.compile(r'\b(twitter|x\.com)[\s/]*@?[A-Za-z0-9_]{1,15}\b', re.IGNORECASE),
                # Instagram
                re.compile(r'\b(instagram|insta|ig)[\s/]*@?[A-Za-z0-9_.]{1,30}\b', re.IGNORECASE),
                # Facebook
                re.compile(r'\b(facebook|fb)[\s/]*[A-Za-z0-9.]{1,50}\b', re.IGNORECASE),
                # TikTok
                re.compile(r'\b(tiktok|tt)[\s/]*@?[A-Za-z0-9_.]{1,24}\b', re.IGNORECASE),
                # LinkedIn
                re.compile(r'\b(linkedin|in)[\s/]*[A-Za-z0-9-]{3,100}\b', re.IGNORECASE),
                # YouTube
                re.compile(r'\b(youtube|yt)[\s/]*[A-Za-z0-9_-]{1,100}\b', re.IGNORECASE),
                # Snapchat
                re.compile(r'\b(snapchat|snap)[\s/]*[A-Za-z0-9._-]{1,15}\b', re.IGNORECASE),
                # General social handle pattern
                re.compile(r'\b(follow|add|find)\s+me\s+(on\s+)?@?[A-Za-z0-9_.]{3,30}\b', re.IGNORECASE),
            ],
            
            'messaging_apps': [
                # WhatsApp
                re.compile(r'\b(whatsapp|whats app|wa)[\s:]*(me|number|contact)?\s*[\+]?[0-9\s\-\.\(\)]{10,15}\b', re.IGNORECASE),
                # Telegram
                re.compile(r'\b(telegram|tg)[\s/]*@?[A-Za-z0-9_]{5,32}\b', re.IGNORECASE),
                # Discord
                re.compile(r'\b(discord)[\s/]*[A-Za-z0-9_#]{2,32}#[0-9]{4}\b', re.IGNORECASE),
                re.compile(r'\b[A-Za-z0-9_.]{2,32}#[0-9]{4}\b'),  # Discord username#1234
                # Skype
                re.compile(r'\b(skype)[\s/]*[A-Za-z0-9_.:-]{6,32}\b', re.IGNORECASE),
                # WeChat
                re.compile(r'\b(wechat|weixin)[\s/]*[A-Za-z0-9_-]{6,20}\b', re.IGNORECASE),
                # Signal
                re.compile(r'\b(signal)[\s:]*(me|number)?\s*[\+]?[0-9\s\-\.\(\)]{10,15}\b', re.IGNORECASE),
            ],
            
            'websites_urls': [
                # HTTP/HTTPS URLs
                re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+', re.IGNORECASE),
                # Domain names without protocol
                re.compile(r'\b[A-Za-z0-9.-]+\.(com|org|net|edu|gov|mil|int|co|io|me|tv|info|biz)\b', re.IGNORECASE),
                # Website references
                re.compile(r'\b(website|site|blog|domain)[\s:]*[A-Za-z0-9.-]+\.(com|org|net|edu|gov)\b', re.IGNORECASE),
            ],
            
            'other_contact': [
                # Zoom meeting IDs
                re.compile(r'\b(zoom)[\s/]*[0-9\s-]{9,11}\b', re.IGNORECASE),
                # Google Meet links
                re.compile(r'\b(meet\.google\.com|google\s+meet)\b', re.IGNORECASE),
                # General contact prompts
                re.compile(r'\b(contact\s+me|reach\s+me|call\s+me|text\s+me|email\s+me|dm\s+me)\b', re.IGNORECASE),
                # External platform references
                re.compile(r'\b(outside\s+this\s+platform|off\s+platform|external\s+contact)\b', re.IGNORECASE),
            ]
        }
        
        return patterns
    
    def detect_contact_info(self, message: str) -> Dict[str, List[str]]:
        """
        Scan message for contact information
        
        Args:
            message: The message text to scan
            
        Returns:
            Dictionary with detected contact types and matches
        """
        detected = {}
        message_lower = message.lower()
        
        # Check for attempts to bypass detection
        cleaned_message = self._clean_obfuscated_text(message)
        
        for contact_type, pattern_list in self.patterns.items():
            matches = []
            for pattern in pattern_list:
                # Check original message
                found = pattern.findall(message)
                matches.extend(found)
                
                # Check cleaned message (for obfuscated content)
                found_cleaned = pattern.findall(cleaned_message)
                matches.extend(found_cleaned)
            
            if matches:
                detected[contact_type] = list(set(matches))  # Remove duplicates
        
        return detected
    
    def _clean_obfuscated_text(self, text: str) -> str:
        """
        Clean obfuscated text to detect hidden contact information
        """
        # Common obfuscation techniques
        substitutions = {
            ' at ': '@',
            ' AT ': '@',
            '[at]': '@',
            '(at)': '@',
            ' dot ': '.',
            ' DOT ': '.',
            '[dot]': '.',
            '(dot)': '.',
            ' dash ': '-',
            ' underscore ': '_',
            ' plus ': '+',
        }
        
        cleaned = text
        for old, new in substitutions.items():
            cleaned = cleaned.replace(old, new)
        
        # Remove excessive spaces
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        return cleaned
    
    def is_violation(self, message: str) -> Tuple[bool, Dict[str, List[str]]]:
        """
        Check if message contains contact information violation
        
        Returns:
            Tuple of (is_violation, detected_contacts)
        """
        detected = self.detect_contact_info(message)
        return len(detected) > 0, detected


class ViolationTracker:
    """
    Track user violations and manage warning/suspension system
    """
    
    def __init__(self):
        self.warning_threshold = 1  # First violation = warning
        self.suspension_threshold = 2  # Second violation = suspension
    
    def record_violation(self, user: User, violation_type: str, detected_content: Dict[str, List[str]], message_content: str) -> Dict[str, any]:
        """
        Record a contact sharing violation for a user
        
        Returns:
            Action taken (warning, suspension, etc.)
        """
        from .models import UserViolation  # Import here to avoid circular imports
        
        # Count existing violations in last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_violations = UserViolation.objects.filter(
            user=user,
            violation_type='contact_sharing',
            created_at__gte=thirty_days_ago
        ).count()
        
        # Create violation record
        violation = UserViolation.objects.create(
            user=user,
            violation_type='contact_sharing',
            violation_data={
                'detected_content': detected_content,
                'message_content': message_content,
                'violation_count': recent_violations + 1
            },
            is_resolved=False
        )
        
        # Determine action based on violation count
        action = self._determine_action(recent_violations + 1)
        
        # Apply action
        if action['type'] == 'warning':
            self._send_warning(user, violation, detected_content)
        elif action['type'] == 'suspension':
            self._suspend_user(user, violation)
        
        return action
    
    def _determine_action(self, violation_count: int) -> Dict[str, any]:
        """
        Determine what action to take based on violation count
        """
        if violation_count == 1:
            return {
                'type': 'warning',
                'message': 'First warning: Contact information sharing detected',
                'severity': 'medium'
            }
        elif violation_count >= 2:
            return {
                'type': 'suspension',
                'message': 'Account suspended for repeated contact information sharing',
                'severity': 'high',
                'duration_days': 7  # 7-day suspension
            }
        else:
            return {
                'type': 'block',
                'message': 'Message blocked for contact information',
                'severity': 'low'
            }
    
    def _send_warning(self, user: User, violation, detected_content: Dict[str, List[str]]):
        """
        Send warning to user about contact sharing violation
        """
        from .models import UserNotification
        
        contact_types = ', '.join(detected_content.keys())
        
        UserNotification.objects.create(
            user=user,
            title='⚠️ Contact Information Sharing Warning',
            message=f"""
            WARNING: Your message was blocked for sharing contact information ({contact_types}).
            
            Our platform prohibits sharing:
            • Email addresses
            • Phone numbers  
            • Social media handles
            • Messaging app contacts
            • External websites
            
            This is your FIRST and FINAL warning. If this happens again, your account will be SUSPENDED.
            
            Please communicate only through our secure messaging system.
            """,
            notification_type='warning',
            is_read=False
        )
        
        logger.warning(f"Contact sharing warning sent to user {user.username} for: {contact_types}")
    
    def _suspend_user(self, user: User, violation):
        """
        Suspend user account for repeated violations
        """
        from .models import UserSuspension, UserNotification
        
        suspension_end = timezone.now() + timedelta(days=7)
        
        # Create suspension record
        UserSuspension.objects.create(
            user=user,
            reason='Repeated contact information sharing violations',
            suspended_by=None,  # System suspension
            suspension_end=suspension_end,
            is_active=True
        )
        
        # Deactivate user account
        user.is_active = False
        user.save()
        
        # Send suspension notification
        UserNotification.objects.create(
            user=user,
            title='🚫 Account Suspended',
            message=f"""
            Your account has been SUSPENDED until {suspension_end.strftime('%B %d, %Y at %I:%M %p')}.
            
            Reason: Repeated contact information sharing violations
            
            You ignored our warning and continued to share contact information, which violates our platform rules.
            
            Your account will be automatically reactivated after the suspension period.
            
            Future violations may result in permanent account termination.
            """,
            notification_type='suspension',
            is_read=False
        )
        
        logger.critical(f"User {user.username} suspended for repeated contact sharing violations")


class ContentModerationService:
    """
    Main service for content moderation integration
    """
    
    def __init__(self):
        self.detector = ContactInfoDetector()
        self.tracker = ViolationTracker()
    
    def moderate_message(self, user: User, message_content: str) -> Dict[str, any]:
        """
        Moderate a message for contact information sharing
        
        Returns:
            Moderation result with action taken
        """
        # Check for violations
        is_violation, detected_content = self.detector.is_violation(message_content)
        
        if not is_violation:
            return {
                'allowed': True,
                'action': 'none',
                'message': 'Message approved'
            }
        
        # Record violation and get action
        action = self.tracker.record_violation(
            user=user,
            violation_type='contact_sharing',
            detected_content=detected_content,
            message_content=message_content
        )
        
        # Block the message regardless of action type
        return {
            'allowed': False,
            'action': action['type'],
            'message': action['message'],
            'detected_content': detected_content,
            'severity': action['severity']
        }


# Singleton instance for use across the application
content_moderator = ContentModerationService()