#!/usr/bin/env python
"""
Script to fix Slack integration configurations by adding missing required fields.
This script can help resolve issues with token extraction from user integrations.
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
logger = logging.getLogger('slack_integration_fixer')

# Load environment variables
load_dotenv()

# Configure Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alyaprojet.settings')
django.setup()

def fix_slack_integration(user_id=None):
    """
    Fix the Slack integration configuration by adding missing required fields.
    
    Args:
        user_id (int, optional): User ID to fix. If None, fixes all enabled Slack integrations.
    """
    from alyawebapp.models import Integration, UserIntegration, CustomUser
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    # Get Slack client ID and secret from .env
    SLACK_CLIENT_ID = os.getenv('SLACK_CLIENT_ID')
    SLACK_CLIENT_SECRET = os.getenv('SLACK_CLIENT_SECRET')
    SLACK_REDIRECT_URI = os.getenv('SLACK_REDIRECT_URI')
    
    # Check for alternative environment variable names
    if not SLACK_CLIENT_ID:
        SLACK_CLIENT_ID = os.getenv('SLACK_SECRET_ID') or os.getenv('SLACK_API_KEY')
    
    # Manual entry if environment variables not found
    if not SLACK_CLIENT_ID:
        logger.warning("⚠️ SLACK_CLIENT_ID not found in environment variables.")
        SLACK_CLIENT_ID = input("Enter Slack Client ID: ").strip()
    
    if not SLACK_CLIENT_SECRET:
        logger.warning("⚠️ SLACK_CLIENT_SECRET not found in environment variables.")
        SLACK_CLIENT_SECRET = input("Enter Slack Client Secret: ").strip()
    
    if not SLACK_REDIRECT_URI:
        logger.warning("⚠️ SLACK_REDIRECT_URI not found in environment variables.")
        SLACK_REDIRECT_URI = input("Enter Slack Redirect URI: ").strip()
    
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
                
                logger.info(f"✅ Fixing Slack integration for user: {user.username or user.email} (ID: {user.id})")
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
                    continue
            
            # Initialize config if it's None
            if config is None:
                logger.warning(f"⚠️ Configuration is None, initializing empty dictionary")
                config = {}
            
            # Ensure config is a dictionary
            if not isinstance(config, dict):
                logger.error(f"❌ Configuration is not a dictionary: {type(config)}")
                continue
            
            # Check for access_token and skip if not present
            if 'access_token' not in config or not config['access_token']:
                logger.error(f"❌ No access_token found in configuration for {username}")
                continue
            
            # Add missing fields
            changes_made = False
            
            if 'client_id' not in config or not config['client_id']:
                logger.info(f"Adding client_id to config")
                config['client_id'] = SLACK_CLIENT_ID
                changes_made = True
            
            if 'client_secret' not in config or not config['client_secret']:
                logger.info(f"Adding client_secret to config")
                config['client_secret'] = SLACK_CLIENT_SECRET
                changes_made = True
            
            if 'redirect_uri' not in config or not config['redirect_uri']:
                logger.info(f"Adding redirect_uri to config")
                config['redirect_uri'] = SLACK_REDIRECT_URI
                changes_made = True
            
            # Update the user integration if changes were made
            if changes_made:
                ui.config = config
                ui.save()
                logger.info(f"✅ Updated configuration for {username}")
                fixed_count += 1
            else:
                logger.info(f"✅ No changes needed for {username} - configuration appears complete")
        
        logger.info(f"\n{'='*50}")
        logger.info(f"✅ Process completed. Fixed {fixed_count} out of {user_integrations.count()} integrations.")
        
        # Final verification step
        if fixed_count > 0:
            logger.info("\nVerifying fixes...")
            for ui in user_integrations:
                try:
                    username = ui.user.username or ui.user.email or f"User ID: {ui.user_id}"
                except:
                    username = f"User ID: {ui.user_id}"
                
                config = ui.config
                if isinstance(config, str):
                    try:
                        config = json.loads(config)
                    except:
                        logger.error(f"❌ Config still not valid JSON for {username}")
                        continue
                
                if not isinstance(config, dict):
                    logger.error(f"❌ Config still not a dictionary for {username}")
                    continue
                
                missing_fields = []
                for field in ['client_id', 'client_secret', 'redirect_uri', 'access_token']:
                    if field not in config or not config[field]:
                        missing_fields.append(field)
                
                if missing_fields:
                    logger.warning(f"⚠️ {username} still missing: {', '.join(missing_fields)}")
                else:
                    logger.info(f"✅ {username} has all required fields")
                
                # Test config with Slack fields validation
                try:
                    from alyawebapp.integrations.slack.handler import SlackHandler as SlackAPI
                    validation_result = SlackAPI.validate_config(None, config)
                    if validation_result['valid']:
                        logger.info(f"✅ Configuration for {username} passes SlackAPI validation")
                    else:
                        logger.warning(f"⚠️ Configuration for {username} fails SlackAPI validation: {validation_result.get('error', 'Unknown reason')}")
                except Exception as e:
                    logger.error(f"❌ Error testing configuration validation: {str(e)}")
        
        # Next steps
        logger.info("\nNext steps:")
        logger.info("1. Run 'python diagnose_slack_token.py' to check if issues are resolved")
        logger.info("2. If problems persist, you may need to reauthorize the Slack integration")
    
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    print("=== SLACK INTEGRATION FIXER ===\n")
    
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
    print("\n⚠️ This script will modify the database to fix Slack integration configurations.")
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
            fix_slack_integration(user_id)
        except Exception as e:
            print(f"Error: {str(e)}")
            fix_slack_integration(None)  # Fix all users if input is invalid
    else:
        fix_slack_integration(None)  # Fix all users 