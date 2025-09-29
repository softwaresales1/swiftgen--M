#!/usr/bin/env python
"""
Migration Check Script for SwiftTalentForge
This script helps verify and apply database migrations for the content moderation system.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Work.settings')
django.setup()

from django.core.management import execute_from_command_line
from django.db import connection
from django.core.management.color import color_style

def check_tables():
    """Check if content moderation tables exist"""
    style = color_style()
    
    required_tables = [
        'Portal_userviolation',
        'Portal_usersuspension', 
        'Portal_contentmoderationlog',
        'Portal_usernotification'
    ]
    
    print(style.HTTP_INFO("Checking database tables..."))
    
    with connection.cursor() as cursor:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        existing_tables = [row[0] for row in cursor.fetchall()]
    
    missing_tables = [table for table in required_tables if table not in existing_tables]
    
    if missing_tables:
        print(style.ERROR(f"Missing tables: {', '.join(missing_tables)}"))
        print(style.WARNING("Database migrations need to be applied!"))
        return False
    else:
        print(style.SUCCESS("All content moderation tables exist!"))
        return True

def apply_migrations():
    """Apply pending migrations"""
    style = color_style()
    print(style.HTTP_INFO("Applying database migrations..."))
    
    try:
        execute_from_command_line(['manage.py', 'migrate'])
        print(style.SUCCESS("Migrations applied successfully!"))
        return True
    except Exception as e:
        print(style.ERROR(f"Error applying migrations: {e}"))
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("SwiftTalentForge Content Moderation Migration Check")
    print("=" * 60)
    
    if not check_tables():
        print("\nApplying migrations...")
        if apply_migrations():
            print("\n" + "=" * 60)
            print("✅ Migration completed! Content moderation should now work.")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("❌ Migration failed! Please check the error above.")
            print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("✅ Database is up to date! Content moderation should work.")
        print("=" * 60)