# Support System Initial Data Setup
# Run this script after migrations to populate initial support data

from django.core.management.base import BaseCommand
from Portal.models import SupportCategory, BotResponse, SupportKnowledgeBase

def setup_support_categories():
    """Create initial support categories"""
    categories = [
        {
            'name': 'Payment & Billing',
            'slug': 'payment-billing',
            'description': 'Payment processing, billing issues, refunds, and transaction problems',
            'icon': 'fas fa-credit-card',
            'sort_order': 1
        },
        {
            'name': 'Account Management',
            'slug': 'account',
            'description': 'Account settings, profile updates, login issues, and verification',
            'icon': 'fas fa-user-cog',
            'sort_order': 2
        },
        {
            'name': 'Project Support',
            'slug': 'projects',
            'description': 'Project creation, management, disputes, and collaboration issues',
            'icon': 'fas fa-project-diagram',
            'sort_order': 3
        },
        {
            'name': 'Technical Issues',
            'slug': 'technical',
            'description': 'Website bugs, performance issues, and technical problems',
            'icon': 'fas fa-bug',
            'sort_order': 4
        },
        {
            'name': 'General Questions',
            'slug': 'general',
            'description': 'General platform questions and information requests',
            'icon': 'fas fa-question-circle',
            'sort_order': 5
        }
    ]
    
    for cat_data in categories:
        category, created = SupportCategory.objects.get_or_create(
            slug=cat_data['slug'],
            defaults=cat_data
        )
        if created:
            print(f"Created category: {category.name}")
        else:
            print(f"Category already exists: {category.name}")
    
    return SupportCategory.objects.all()

def setup_bot_responses(categories):
    """Create initial bot responses"""
    
    # Get categories
    payment_cat = categories.get(slug='payment-billing')
    account_cat = categories.get(slug='account')
    project_cat = categories.get(slug='projects')
    technical_cat = categories.get(slug='technical')
    general_cat = categories.get(slug='general')
    
    responses = [
        # Payment & Billing Responses
        {
            'category': payment_cat,
            'name': 'Payment Processing Issues',
            'trigger_keywords': ['payment', 'billing', 'charge', 'transaction', 'refund', 'money'],
            'trigger_patterns': r'payment.*(?:failed|error|problem|issue)|billing.*problem|transaction.*(?:failed|error)',
            'response_text': '''I understand you're experiencing payment issues. I can help with:

• Transaction processing problems
• Billing questions and disputes
• Refund requests
• Payment method updates
• Stuck or pending payments

For urgent payment issues or disputes requiring immediate attention, please contact our payment specialists at **info@swifttalentforge.com** with:
- Your transaction ID
- Description of the issue
- Screenshots (if applicable)

Our payment team will resolve your issue within 24 hours.''',
            'suggest_escalation': True,
            'priority': 10
        },
        {
            'category': payment_cat,
            'name': 'Refund Requests',
            'trigger_keywords': ['refund', 'money back', 'return', 'cancel payment'],
            'response_text': '''I can help you with refund requests. Our refund policy depends on the project status:

**Before work starts:** Full refund available
**Work in progress:** Partial refund based on completion
**Work completed:** Refunds handled case-by-case

To process your refund request, please email **info@swifttalentforge.com** with:
- Project ID and details
- Reason for refund request
- Your preferred refund method

Our team will review and respond within 48 hours.''',
            'suggest_escalation': True,
            'priority': 9
        },
        
        # Account Management Responses
        {
            'category': account_cat,
            'name': 'Login and Password Issues',
            'trigger_keywords': ['login', 'password', 'forgot', 'access', 'locked', 'reset'],
            'trigger_patterns': r'(?:can\'t|cannot).*login|forgot.*password|password.*(?:reset|problem)|account.*locked',
            'response_text': '''I can help you regain access to your account:

**Password Reset:**
1. Go to the login page
2. Click "Forgot Password"
3. Enter your email address
4. Check your email for reset instructions

**Account Locked:** If your account is locked, please email **info@swifttalentforge.com** with your username.

**Still Having Issues?** Contact our support team at **info@swifttalentforge.com** for immediate assistance.''',
            'suggest_escalation': False,
            'priority': 8
        },
        {
            'category': account_cat,
            'name': 'Profile and Verification',
            'trigger_keywords': ['profile', 'verification', 'verify', 'identity', 'documents'],
            'response_text': '''I can help with profile and verification issues:

**Profile Updates:** You can update most profile information in your account settings.

**Identity Verification:** Upload clear photos of:
- Government-issued ID
- Proof of address (utility bill, bank statement)

**Verification Delays:** If your verification is taking longer than 48 hours, please contact **info@swifttalentforge.com** with your account details.

**Need Help?** Our team is available 24/7 to assist with verification issues.''',
            'suggest_escalation': False,
            'priority': 7
        },
        
        # Project Support Responses
        {
            'category': project_cat,
            'name': 'Project Disputes',
            'trigger_keywords': ['dispute', 'disagreement', 'problem with freelancer', 'problem with client', 'mediation'],
            'trigger_patterns': r'dispute.*(?:freelancer|client|project)|(?:freelancer|client).*(?:problem|issue|dispute)',
            'response_text': '''I understand you're having a dispute. SwiftTalentForge offers mediation services:

**Before Escalating:**
- Try communicating directly through our messaging system
- Review the project requirements and deliverables
- Check milestone agreements

**Dispute Resolution:**
For disputes requiring mediation, please email **info@swifttalentforge.com** with:
- Project ID and details
- Description of the issue
- Supporting documentation/screenshots
- Your preferred resolution

Our mediation team will review and respond within 24 hours.''',
            'suggest_escalation': True,
            'require_human_followup': True,
            'priority': 10
        },
        {
            'category': project_cat,
            'name': 'Project Management Help',
            'trigger_keywords': ['project', 'milestone', 'deadline', 'deliverable', 'task'],
            'response_text': '''I can help with project management questions:

**Project Setup:**
- Creating clear project descriptions
- Setting realistic milestones
- Defining deliverables

**Communication:**
- Use our built-in messaging system
- Schedule regular check-ins
- Document all changes

**Payments:**
- Payments are held in escrow until milestones are completed
- Release payments after reviewing deliverables

**Need Specific Help?** Contact **info@swifttalentforge.com** for personalized project assistance.''',
            'suggest_escalation': False,
            'priority': 6
        },
        
        # Technical Issues
        {
            'category': technical_cat,
            'name': 'Website Issues',
            'trigger_keywords': ['bug', 'error', 'broken', 'not working', 'slow', 'loading'],
            'trigger_patterns': r'(?:website|site|page).*(?:not working|broken|error|slow)|bug|error.*(?:message|code)',
            'response_text': '''I'm sorry you're experiencing technical issues. Here's how to get help:

**Common Solutions:**
- Clear your browser cache and cookies
- Try a different browser or incognito mode
- Check your internet connection
- Disable browser extensions temporarily

**Still Having Issues?**
Please email **info@swifttalentforge.com** with:
- Description of the problem
- Your browser and operating system
- Screenshots of any error messages
- Steps to reproduce the issue

Our technical team will investigate and respond quickly.''',
            'suggest_escalation': True,
            'priority': 8
        },
        
        # General Responses
        {
            'category': general_cat,
            'name': 'Platform Information',
            'trigger_keywords': ['how does', 'what is', 'explain', 'how to', 'information'],
            'response_text': '''I'm happy to help explain how SwiftTalentForge works:

**For Clients:**
- Post projects with clear requirements
- Review freelancer proposals
- Hire the best candidates
- Pay securely through escrow

**For Freelancers:**
- Browse available projects
- Submit competitive proposals
- Deliver quality work
- Get paid reliably

**Getting Started:**
1. Complete your profile
2. Verify your identity
3. Start browsing/posting projects

**Need More Help?** Contact **info@swifttalentforge.com** or check our knowledge base for detailed guides.''',
            'suggest_escalation': False,
            'priority': 5
        },
        {
            'category': None,  # General fallback
            'name': 'Greeting and Welcome',
            'trigger_keywords': ['hello', 'hi', 'hey', 'help', 'support'],
            'response_text': '''Hello! I'm your AI support assistant for SwiftTalentForge. I'm here to help you 24/7 with:

• Payment and billing questions
• Account management issues
• Project support and disputes
• Technical problems
• General platform information

How can I assist you today? Feel free to describe your issue, and I'll do my best to help or connect you with our human support team when needed.''',
            'suggest_escalation': False,
            'priority': 5
        }
    ]
    
    for response_data in responses:
        # Convert lists to proper format
        if 'trigger_keywords' in response_data:
            response_data['trigger_keywords'] = response_data['trigger_keywords']
        
        bot_response, created = BotResponse.objects.get_or_create(
            name=response_data['name'],
            defaults=response_data
        )
        if created:
            print(f"Created bot response: {bot_response.name}")
        else:
            print(f"Bot response already exists: {bot_response.name}")

def setup_knowledge_base(categories):
    """Create initial knowledge base articles"""
    
    payment_cat = categories.get(slug='payment-billing')
    account_cat = categories.get(slug='account')
    project_cat = categories.get(slug='projects')
    
    articles = [
        {
            'category': payment_cat,
            'title': 'How Payments Work on SwiftTalentForge',
            'slug': 'how-payments-work',
            'summary': 'Complete guide to our secure escrow payment system',
            'content': '''# How Payments Work on SwiftTalentForge

SwiftTalentForge uses a secure escrow system to protect both clients and freelancers:

## For Clients
1. **Deposit Funds**: When you hire a freelancer, deposit project funds into escrow
2. **Funds Held Safely**: Money is held securely until work is completed
3. **Review & Release**: Review deliverables and release payment when satisfied

## For Freelancers
1. **Secured Payment**: Funds are guaranteed once deposited by client
2. **Milestone Payments**: Get paid as you complete project milestones
3. **Fast Withdrawal**: Withdraw earnings quickly to your preferred method

## Payment Methods
- Credit/Debit Cards (Visa, MasterCard, American Express)
- PayPal
- Bank Transfer (for larger amounts)

## Security Features
- SSL encryption for all transactions
- PCI DSS compliant payment processing
- Fraud detection and prevention
- 24/7 payment monitoring

## Need Help?
Contact our payment support team at info@swifttalentforge.com for any payment-related questions.''',
            'article_type': 'guide',
            'search_keywords': ['payment', 'escrow', 'deposit', 'withdraw', 'secure', 'money'],
            'featured': True,
            'is_published': True
        },
        {
            'category': account_cat,
            'title': 'Getting Started on SwiftTalentForge',
            'slug': 'getting-started',
            'summary': 'Step-by-step guide for new users',
            'content': '''# Getting Started on SwiftTalentForge

Welcome to SwiftTalentForge! Follow these steps to get started:

## Step 1: Create Your Account
1. Sign up with your email address
2. Choose a strong password
3. Verify your email address

## Step 2: Complete Your Profile
1. Add a professional profile photo
2. Write a compelling bio
3. Add your skills and experience
4. Upload portfolio samples (for freelancers)

## Step 3: Identity Verification
1. Upload a government-issued ID
2. Provide proof of address
3. Wait for verification (usually 24-48 hours)

## Step 4: Start Using the Platform

### For Clients:
1. Post your first project
2. Set a clear budget and timeline
3. Review freelancer proposals
4. Hire the best candidate

### For Freelancers:
1. Browse available projects
2. Submit compelling proposals
3. Build client relationships
4. Deliver quality work

## Tips for Success
- Complete your profile 100%
- Be responsive to messages
- Maintain professional communication
- Deliver work on time

## Need Help?
Our support team is available 24/7 at info@swifttalentforge.com''',
            'article_type': 'guide',
            'search_keywords': ['getting started', 'new user', 'setup', 'account', 'verification'],
            'featured': True,
            'is_published': True
        }
    ]
    
    for article_data in articles:
        article, created = SupportKnowledgeBase.objects.get_or_create(
            slug=article_data['slug'],
            defaults=article_data
        )
        if created:
            print(f"Created knowledge base article: {article.title}")
        else:
            print(f"Knowledge base article already exists: {article.title}")

def main():
    """Main setup function"""
    print("Setting up SwiftTalentForge Support System...")
    
    print("\n1. Creating support categories...")
    categories = setup_support_categories()
    
    print("\n2. Creating bot responses...")
    setup_bot_responses(categories)
    
    print("\n3. Creating knowledge base articles...")
    setup_knowledge_base(categories)
    
    print("\n✅ Support system setup complete!")
    print("\nTo test the system:")
    print("1. Run migrations: python manage.py makemigrations && python manage.py migrate")
    print("2. Load this data: python manage.py shell < setup_support_data.py")
    print("3. Visit your website and try the support widget")

if __name__ == "__main__":
    main()