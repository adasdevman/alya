#!/usr/bin/env python
"""
Script to fix Slack token storage issue.
This script moves the access token from the separate access_token field
into the config dictionary where the SlackHandler expects to find it.
"""

import os
import sys
import json
import django
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('slack_token_field_fixer')

# Load environment variables
load_dotenv()

# Configure Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alyaprojet.settings')
django.setup()

def fix_slack_token_field(user_id=None):
    """
    Fix the issue where the Slack token is stored in the access_token field
    but not in the config dictionary where the SlackHandler looks for it.
    
    Args:
        user_id (int, optional): User ID to fix. If None, fixes all enabled Slack integrations.
    """
    from alyawebapp.models import Integration, UserIntegration, CustomUser
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    try:
        # Find Slack integration
        try:
            slack_integration = Integration.objects.get(name__iexact='slack')
            logger.info(f"✅ Found Slack integration: {slack_integration.name} (ID: {slack_integration.id})")
        except Integration.DoesNotExist:
            logger.error("❌ No Slack integration found in the database.")
            return
        except Integration.MultipleObjectsReturned:
            logger.warning("⚠️ Multiple Slack integrations found. Using the first one.")
            slack_integration = Integration.objects.filter(name__icontains='slack').first()
        
        # Query user integrations
        if user_id:
            try:
                if isinstance(user_id, str) and not user_id.isdigit():
                    # Try to find user by username or email
                    user = User.objects.filter(username=user_id).first() or User.objects.filter(email=user_id).first()
                    if not user:
                        logger.error(f"❌ User '{user_id}' not found.")
                        return
                    user_id = user.id
                else:
                    user_id = int(user_id)
                    user = User.objects.get(id=user_id)
                
                logger.info(f"✅ Fixing Slack token field for user: {user.username or user.email} (ID: {user.id})")
                user_integrations = UserIntegration.objects.filter(
                    user_id=user.id,
                    integration=slack_integration,
                    enabled=True
                )
            except User.DoesNotExist:
                logger.error(f"❌ User with ID {user_id} not found.")
                return
        else:
            # Get all enabled Slack integrations
            user_integrations = UserIntegration.objects.filter(
                integration=slack_integration,
                enabled=True
            )
        
        if not user_integrations.exists():
            logger.error("❌ No enabled user integrations found for Slack.")
            return
        
        logger.info(f"Found {user_integrations.count()} enabled Slack integrations to process.")
        
        # Fix each user integration
        fixed_count = 0
        for ui in user_integrations:
            try:
                username = ui.user.username or ui.user.email or f"User ID: {ui.user_id}"
            except:
                username = f"User ID: {ui.user_id}"
            
            logger.info(f"\n{'='*50}\nProcessing Slack integration for {username}")
            
            # Check if there's an access_token field but it's not in config
            access_token = None
            
            # Get the access_token from the dedicated field
            try:
                if hasattr(ui, 'access_token') and ui.access_token:
                    access_token = ui.access_token
                    logger.info(f"✅ Found access token in separate field: {access_token[:10]}...{access_token[-5:]}")
            except Exception as e:
                logger.error(f"❌ Error accessing access_token field: {str(e)}")
            
            if not access_token:
                logger.warning(f"⚠️ No access token found in separate field for {username}")
                continue
                
            # Get the current config
            config = ui.config
            
            # Convert string configs to dict
            if isinstance(config, str):
                logger.info(f"Configuration is a string, attempting to parse as JSON")
                try:
                    config = json.loads(config)
                    logger.info(f"✅ Successfully parsed JSON configuration")
                except json.JSONDecodeError:
                    logger.error(f"❌ Failed to parse configuration as JSON: {config[:100]}...")
                    # Initialize empty dict if parsing fails
                    config = {}
            
            # Initialize config if it's None
            if config is None:
                logger.warning(f"⚠️ Configuration is None, initializing empty dictionary")
                config = {}
            
            # Ensure config is a dictionary
            if not isinstance(config, dict):
                logger.error(f"❌ Configuration is not a dictionary: {type(config)}")
                config = {}
            
            # Add access_token to config if not already there
            if 'access_token' not in config or not config['access_token']:
                logger.info(f"Adding access_token to config dictionary")
                config['access_token'] = access_token
                
                # Add other required fields with default values if they don't exist
                if 'client_id' not in config:
                    config['client_id'] = os.getenv('SLACK_CLIENT_ID') or os.getenv('SLACK_SECRET_ID') or 'default_id'
                    logger.info(f"Adding default client_id to config")
                
                if 'client_secret' not in config:
                    config['client_secret'] = os.getenv('SLACK_CLIENT_SECRET') or 'default_secret'
                    logger.info(f"Adding default client_secret to config")
                
                if 'redirect_uri' not in config:
                    config['redirect_uri'] = os.getenv('SLACK_REDIRECT_URI') or 'default_uri'
                    logger.info(f"Adding default redirect_uri to config")
                
                # Update the user integration
                ui.config = config
                ui.save()
                logger.info(f"✅ Updated configuration for {username}")
                fixed_count += 1
            else:
                # Check if the tokens match
                if config['access_token'] != access_token:
                    logger.warning(f"⚠️ access_token in config doesn't match the one in the separate field")
                    logger.info(f"Updating access_token in config")
                    config['access_token'] = access_token
                    ui.config = config
                    ui.save()
                    logger.info(f"✅ Updated access_token in config for {username}")
                    fixed_count += 1
                else:
                    logger.info(f"✅ No changes needed for {username} - token already in config")
        
        logger.info(f"\n{'='*50}")
        logger.info(f"✅ Process completed. Fixed {fixed_count} out of {user_integrations.count()} integrations.")
        
        if fixed_count > 0:
            # Run diagnose_slack_token.py to check if the issue is resolved
            logger.info("\nVerifying fixes...")
            try:
                from diagnose_slack_token import diagnose_slack_token
                if user_id:
                    diagnose_slack_token(user_id)
                else:
                    # Only check the ones we fixed
                    for ui in user_integrations:
                        if hasattr(ui, 'user') and hasattr(ui.user, 'id'):
                            diagnose_slack_token(ui.user.id)
            except ImportError:
                logger.warning("⚠️ Could not import diagnose_slack_token.py to verify fixes")
        
        # Next steps
        logger.info("\nNext steps:")
        logger.info("1. Run 'python diagnose_slack_token.py' to check if issues are resolved")
        logger.info("2. Run 'python test_slack_integration.py' to test sending a message")
        logger.info("3. If problems persist, you may need to reauthorize the Slack integration")
    
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    print("=== SLACK TOKEN FIELD FIXER ===\n")
    
    # Get list of users
    from django.contrib.auth import get_user_model
    User = get_user_model()
    users = User.objects.all()
    
    print(f"Available users ({users.count()}):")
    for i, user in enumerate(users, 1):
        display_name = user.username or user.email or f"User {user.id}"
        print(f"{i}. ID: {user.id}, Name: {display_name}")
    
    # Get user input for which user to fix
    user_input = input("\nEnter user ID or number to fix (or press Enter for all users): ").strip()
    
    # Confirm action
    print("\n⚠️ This script will modify the database to fix Slack token field issues.")
    confirm = input("Are you sure you want to proceed? (y/n): ").strip().lower()
    
    if confirm != 'y':
        print("Operation cancelled.")
        sys.exit(0)
    
    if user_input:
        # Check if it's a number from the list
        try:
            if user_input.isdigit() and 1 <= int(user_input) <= users.count():
                user_id = users[int(user_input) - 1].id
            else:
                user_id = user_input
            fix_slack_token_field(user_id)
        except Exception as e:
            print(f"Error: {str(e)}")
            fix_slack_token_field(None)  # Fix all users if input is invalid
    else:
        fix_slack_token_field(None)  # Fix all users 