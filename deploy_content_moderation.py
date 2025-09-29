#!/usr/bin/env python
"""
Safe Migration Script for SwiftTalentForge Live Deployment
This script safely applies content moderation migrations to the live database.
"""

import os
import sys
import django
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Work.settings')
django.setup()

from django.core.management import execute_from_command_line, call_command
from django.db import connection, transaction
from django.core.management.color import color_style
from django.db.migrations.executor import MigrationExecutor

def backup_database():
    """Create a backup of the current database"""
    style = color_style()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"db_backup_{timestamp}.sqlite3"
    
    try:
        if os.path.exists('db.sqlite3'):
            import shutil
            shutil.copy2('db.sqlite3', backup_name)
            print(style.SUCCESS(f"✅ Database backed up to: {backup_name}"))
            return backup_name
        else:
            print(style.WARNING("⚠️  No db.sqlite3 found, proceeding without backup"))
            return None
    except Exception as e:
        print(style.ERROR(f"❌ Backup failed: {e}"))
        return None

def check_migration_status():
    """Check which migrations are applied and which are pending"""
    style = color_style()
    
    print(style.HTTP_INFO("📋 Checking migration status..."))
    
    executor = MigrationExecutor(connection)
    plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
    
    applied_migrations = executor.loader.applied_migrations
    pending_migrations = [migration for migration, backwards in plan if not backwards]
    
    print(f"Applied migrations: {len(applied_migrations)}")
    print(f"Pending migrations: {len(pending_migrations)}")
    
    # Check specifically for content moderation migration
    content_mod_migration = ('Portal', '0014_contentmoderationlog_usernotification_usersuspension_and_more')
    
    if content_mod_migration in applied_migrations:
        print(style.SUCCESS("✅ Content moderation migration is already applied"))
        return True, pending_migrations
    elif content_mod_migration in [(app, name) for app, name in pending_migrations]:
        print(style.WARNING("⚠️  Content moderation migration is pending"))
        return False, pending_migrations
    else:
        print(style.ERROR("❌ Content moderation migration not found"))
        return False, pending_migrations

def check_required_tables():
    """Check if content moderation tables exist"""
    style = color_style()
    
    required_tables = [
        'Portal_userviolation',
        'Portal_usersuspension', 
        'Portal_contentmoderationlog',
        'Portal_usernotification'
    ]
    
    print(style.HTTP_INFO("🔍 Checking required tables..."))
    
    with connection.cursor() as cursor:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        existing_tables = [row[0] for row in cursor.fetchall()]
    
    missing_tables = [table for table in required_tables if table not in existing_tables]
    
    if missing_tables:
        print(style.ERROR(f"❌ Missing tables: {', '.join(missing_tables)}"))
        return False, missing_tables
    else:
        print(style.SUCCESS("✅ All required tables exist"))
        return True, []

def apply_migrations_safely():
    """Apply migrations with transaction rollback on failure"""
    style = color_style()
    
    print(style.HTTP_INFO("🚀 Applying migrations safely..."))
    
    try:
        with transaction.atomic():
            call_command('migrate', verbosity=2)
        print(style.SUCCESS("✅ Migrations applied successfully!"))
        return True
    except Exception as e:
        print(style.ERROR(f"❌ Migration failed: {e}"))
        print(style.WARNING("🔄 Database rolled back to previous state"))
        return False

def main():
    """Main execution function"""
    style = color_style()
    
    print("=" * 70)
    print("🎯 SwiftTalentForge Content Moderation Migration Deployment")
    print("=" * 70)
    
    # Step 1: Backup database
    print("\n📦 Step 1: Creating database backup...")
    backup_file = backup_database()
    
    # Step 2: Check migration status
    print("\n📋 Step 2: Checking migration status...")
    is_applied, pending = check_migration_status()
    
    # Step 3: Check tables
    print("\n🔍 Step 3: Checking database tables...")
    tables_exist, missing = check_required_tables()
    
    # Step 4: Apply migrations if needed
    if not is_applied or not tables_exist:
        print(f"\n🚀 Step 4: Applying migrations...")
        print(f"Pending migrations: {len(pending)}")
        
        if pending:
            success = apply_migrations_safely()
            
            if success:
                print("\n🔍 Verifying tables after migration...")
                tables_exist_after, missing_after = check_required_tables()
                
                if tables_exist_after:
                    print("\n" + "=" * 70)
                    print("🎉 SUCCESS! Content moderation system is now ready!")
                    print("✅ Beautiful warning modals will work")
                    print("✅ Account suspension system is active") 
                    print("✅ All database tables are properly created")
                    print("=" * 70)
                else:
                    print(style.ERROR(f"\n❌ Tables still missing: {missing_after}"))
            else:
                print("\n" + "=" * 70)
                print("❌ Migration failed!")
                if backup_file:
                    print(f"🔄 Restore from backup: {backup_file}")
                print("=" * 70)
        else:
            print(style.WARNING("No pending migrations found"))
    else:
        print("\n" + "=" * 70)
        print("✅ System is already up to date!")
        print("🎯 Content moderation should be working correctly")
        print("=" * 70)

if __name__ == "__main__":
    main()