#!/usr/bin/env python
"""
Diagnostic script to troubleshoot Slack token extraction from user integration.
This script examines the structure of the Slack integration config and displays
detailed information about token retrieval.
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
logger = logging.getLogger('slack_token_diagnostics')

# Load environment variables
load_dotenv()

# Configure Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alyaprojet.settings')
django.setup()

def diagnose_slack_token(user_id=None):
    """
    Diagnose issues with Slack token retrieval for a specific user or all users.
    
    Args:
        user_id (int, optional): User ID to check. If None, checks all users with Slack integration.
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
        
        # If user_id is provided, check only that user
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
                
                logger.info(f"✅ Checking Slack token for user: {user.username or user.email} (ID: {user.id})")
                user_integrations = UserIntegration.objects.filter(
                    user_id=user.id,
                    integration=slack_integration
                )
            except User.DoesNotExist:
                logger.error(f"❌ User with ID {user_id} not found.")
                return
        else:
            # Check all users with Slack integration
            user_integrations = UserIntegration.objects.filter(integration=slack_integration)
            logger.info(f"Found {user_integrations.count()} users with Slack integration.")
        
        if not user_integrations.exists():
            logger.error("❌ No user integrations found for Slack.")
            return
        
        # Analyze each user integration
        for ui in user_integrations:
            try:
                username = ui.user.username or ui.user.email or f"User ID: {ui.user_id}"
            except:
                username = f"User ID: {ui.user_id}"
            
            logger.info(f"\n{'='*50}\nAnalyzing Slack integration for {username}")
            
            # Check if enabled
            if not ui.enabled:
                logger.warning(f"⚠️ Slack integration is DISABLED for {username}")
                continue
            
            logger.info(f"✅ Slack integration is ENABLED for {username}")
            
            # Examine config structure
            config = ui.config
            logger.info(f"Configuration type: {type(config)}")
            
            if config is None:
                logger.error(f"❌ Configuration is None for {username}")
                continue
            
            if isinstance(config, str):
                logger.info(f"Configuration is a string, attempting to parse as JSON")
                try:
                    config = json.loads(config)
                    logger.info(f"✅ Successfully parsed JSON configuration")
                except json.JSONDecodeError:
                    logger.error(f"❌ Failed to parse configuration as JSON: {config[:100]}...")
                    continue
            
            if not isinstance(config, dict):
                logger.error(f"❌ Configuration is not a dictionary: {type(config)}")
                continue
            
            # Check for access_token
            if 'access_token' not in config:
                logger.error(f"❌ No access_token found in configuration for {username}")
                logger.info(f"Available keys: {', '.join(config.keys())}")
                continue
            
            # Check token format
            token = config['access_token']
            if not token:
                logger.error(f"❌ Empty access_token for {username}")
                continue
            
            # Mask the token for security
            masked_token = f"{token[:10]}...{token[-5:]}" if len(token) > 15 else "***masked***"
            logger.info(f"✅ Found access_token: {masked_token}")
            
            # Check token format
            if token.startswith('xoxb-'):
                logger.info(f"✅ Token has correct bot token prefix (xoxb-)")
            elif token.startswith('xoxp-'):
                logger.info(f"✅ Token has correct user token prefix (xoxp-)")
            elif token.startswith('xoxe.'):
                logger.info(f"✅ Token has correct enterprise token prefix (xoxe.)")
            else:
                logger.warning(f"⚠️ Token has unexpected format: {token[:5]}...")
            
            # Check for refresh_token
            if 'refresh_token' in config and config['refresh_token']:
                logger.info(f"✅ refresh_token is present")
            else:
                logger.warning(f"⚠️ No refresh_token found")
            
            # Check for other required fields
            missing_fields = []
            for field in ['client_id', 'client_secret', 'redirect_uri']:
                if field not in config or not config[field]:
                    missing_fields.append(field)
            
            if missing_fields:
                logger.warning(f"⚠️ Missing fields: {', '.join(missing_fields)}")
            else:
                logger.info(f"✅ All required fields are present")
                
            # Check if there are other fields that might be causing issues
            other_fields = [key for key in config.keys() 
                           if key not in ['access_token', 'refresh_token', 'client_id', 'client_secret', 'redirect_uri']]
            if other_fields:
                logger.info(f"Additional fields in config: {', '.join(other_fields)}")
                
            # If team_id is present, it's likely a valid configuration
            if 'team_id' in config:
                logger.info(f"✅ team_id is present: {config['team_id']}")
                
            # Print full configuration (masked)
            safe_config = config.copy()
            if 'access_token' in safe_config:
                safe_config['access_token'] = masked_token
            if 'refresh_token' in safe_config and safe_config['refresh_token']:
                refresh = safe_config['refresh_token']
                safe_config['refresh_token'] = f"{refresh[:5]}...{refresh[-3:]}" if len(refresh) > 8 else "***masked***"
            if 'client_secret' in safe_config and safe_config['client_secret']:
                secret = safe_config['client_secret']
                safe_config['client_secret'] = f"{secret[:3]}...{secret[-3:]}" if len(secret) > 6 else "***masked***"
                
            logger.info(f"Full configuration (masked):\n{json.dumps(safe_config, indent=2)}")
            
            # Simulate initializing the SlackHandler as would happen in the application
            logger.info("\nSimulating SlackHandler initialization...")
            try:
                # We'll use the minimal_config approach as in the slack_handler.py file
                minimal_config = {
                    'client_id': config.get('client_id', 'default_id'),
                    'client_secret': config.get('client_secret', 'default_secret'),
                    'redirect_uri': config.get('redirect_uri', 'default_uri'),
                    'access_token': config['access_token'],
                    'refresh_token': config.get('refresh_token')
                }
                
                logger.info(f"✅ Created minimal_config successfully")
                
                # Now try to import the SlackHandler class
                try:
                    from alyawebapp.integrations.slack.handler import SlackHandler as SlackAPI
                    logger.info(f"✅ Successfully imported SlackHandler class")
                    
                    # Try to initialize the SlackHandler
                    slack_handler = SlackAPI(minimal_config)
                    logger.info(f"✅ Successfully initialized SlackHandler")
                    
                    # Check if verify_token method works
                    result = slack_handler.verify_token()
                    if result:
                        logger.info(f"✅ Token verification successful")
                    else:
                        logger.warning(f"⚠️ Token verification failed")
                        
                except ImportError as e:
                    logger.error(f"❌ Failed to import SlackHandler: {str(e)}")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize SlackHandler: {str(e)}")
            except Exception as e:
                logger.error(f"❌ Error simulating SlackHandler: {str(e)}")
            
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    print("=== SLACK TOKEN DIAGNOSTICS ===\n")
    
    # Get list of users
    from django.contrib.auth import get_user_model
    User = get_user_model()
    users = User.objects.all()
    
    print(f"Available users ({users.count()}):")
    for i, user in enumerate(users, 1):
        display_name = user.username or user.email or f"User {user.id}"
        print(f"{i}. ID: {user.id}, Name: {display_name}")
    
    # Get user input for which user to check
    user_input = input("\nEnter user ID or number to check (or press Enter for all users): ").strip()
    
    if user_input:
        # Check if it's a number from the list
        try:
            if user_input.isdigit() and 1 <= int(user_input) <= users.count():
                user_id = users[int(user_input) - 1].id
            else:
                user_id = user_input
            diagnose_slack_token(user_id)
        except Exception as e:
            print(f"Error: {str(e)}")
            diagnose_slack_token(None)  # Check all users if input is invalid
    else:
        diagnose_slack_token(None)  # Check all users 