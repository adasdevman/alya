#!/usr/bin/env python
"""
Script to test Slack integration by sending a test message.
This helps verify if the token extraction and message sending works correctly.
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
logger = logging.getLogger('slack_test')

# Load environment variables
load_dotenv()

# Configure Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alyaprojet.settings')
django.setup()

def test_slack_integration(user_id=None, channel=None, message=None):
    """
    Test Slack integration by sending a message.
    
    Args:
        user_id (int, optional): User ID to use for testing. If None, lists users for selection.
        channel (str, optional): Channel to send message to. Default is "general".
        message (str, optional): Message to send. Default is a test message.
    """
    from alyawebapp.models import Integration, UserIntegration, CustomUser
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    # Default values
    if not channel:
        channel = "general"
    if not message:
        message = "Test message from Slack integration test script 🤖"
    
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
        
        # If no user_id provided, list users with Slack integration
        if not user_id:
            user_integrations = UserIntegration.objects.filter(
                integration=slack_integration,
                enabled=True
            ).select_related('user')
            
            if not user_integrations.exists():
                logger.error("❌ No enabled Slack integrations found.")
                return
            
            print("\nUsers with enabled Slack integration:")
            for i, ui in enumerate(user_integrations, 1):
                try:
                    username = ui.user.username or ui.user.email or f"User ID: {ui.user_id}"
                except:
                    username = f"User ID: {ui.user_id}"
                print(f"{i}. {username}")
            
            # Ask for user selection
            selection = input("\nSelect user number to test: ")
            try:
                index = int(selection) - 1
                if index < 0 or index >= user_integrations.count():
                    logger.error("❌ Invalid selection.")
                    return
                
                selected_ui = user_integrations[index]
                user_id = selected_ui.user_id
                logger.info(f"Selected user ID: {user_id}")
            except ValueError:
                logger.error("❌ Please enter a valid number.")
                return
        
        # Get user integration
        user_integration = UserIntegration.objects.filter(
            user_id=user_id,
            integration=slack_integration,
            enabled=True
        ).first()
        
        if not user_integration:
            logger.error(f"❌ No enabled Slack integration found for user ID: {user_id}")
            return
        
        try:
            username = user_integration.user.username or user_integration.user.email or f"User ID: {user_integration.user_id}"
        except:
            username = f"User ID: {user_integration.user_id}"
        
        logger.info(f"✅ Testing Slack integration for: {username}")
        
        # Verify config
        config = user_integration.config
        if isinstance(config, str):
            try:
                config = json.loads(config)
            except json.JSONDecodeError:
                logger.error(f"❌ Failed to parse configuration as JSON.")
                return
        
        if not isinstance(config, dict):
            logger.error(f"❌ Configuration is not a dictionary: {type(config)}")
            return
        
        if 'access_token' not in config or not config['access_token']:
            logger.error(f"❌ No access_token found in configuration.")
            return
        
        # Check required fields
        missing_fields = []
        for field in ['client_id', 'client_secret', 'redirect_uri', 'access_token']:
            if field not in config or not config[field]:
                missing_fields.append(field)
        
        if missing_fields:
            logger.warning(f"⚠️ Missing fields: {', '.join(missing_fields)}")
            logger.info("Consider running fix_slack_integration.py to add missing fields.")
        
        # Create minimal config
        minimal_config = {
            'client_id': config.get('client_id', 'default_id'),
            'client_secret': config.get('client_secret', 'default_secret'),
            'redirect_uri': config.get('redirect_uri', 'default_uri'),
            'access_token': config['access_token'],
            'refresh_token': config.get('refresh_token')
        }
        
        # Import SlackHandler and test
        try:
            from alyawebapp.integrations.slack.handler import SlackHandler as SlackAPI
            logger.info(f"✅ Successfully imported SlackHandler")
            
            # Initialize handler
            slack_handler = SlackAPI(minimal_config)
            logger.info(f"✅ Successfully initialized SlackHandler")
            
            # Verify token
            if not slack_handler.verify_token():
                logger.error("❌ Token verification failed. Token may be invalid or expired.")
                return
            
            logger.info(f"✅ Token verification successful")
            
            # Format channel name
            if not channel.startswith('#') and not channel.startswith('@'):
                channel = '#' + channel
            
            # Send test message
            logger.info(f"Sending test message to channel: {channel}")
            result = slack_handler.send_message(
                channel=channel,
                message=message
            )
            
            # Check result
            if result.get('ok', False):
                logger.info(f"✅ Message sent successfully!")
                logger.info(f"Message timestamp: {result.get('ts')}")
                logger.info(f"Channel: {result.get('channel')}")
                return True
            else:
                error = result.get('error', 'unknown_error')
                logger.error(f"❌ Failed to send message: {error}")
                
                # Provide help based on error type
                if error == 'channel_not_found':
                    logger.error(f"The channel {channel} doesn't exist or the bot doesn't have access to it.")
                    # List available channels
                    try:
                        channels = slack_handler.get_channels()
                        logger.info(f"\nAvailable channels ({len(channels)}):")
                        for i, ch in enumerate(channels[:10], 1):
                            logger.info(f"{i}. #{ch.get('name')} {' (private)' if ch.get('is_private') else ''}")
                        if len(channels) > 10:
                            logger.info(f"...and {len(channels) - 10} more channels")
                    except Exception as e:
                        logger.error(f"Failed to list channels: {str(e)}")
                elif error == 'not_in_channel':
                    logger.error(f"The bot is not a member of the channel {channel}.")
                    logger.info(f"Invite the bot to the channel with /invite @botname")
                elif error == 'invalid_auth':
                    logger.error(f"Invalid authentication. Token may be revoked or expired.")
                    logger.info(f"Try reauthorizing the Slack integration.")
                return False
                
        except ImportError as e:
            logger.error(f"❌ Failed to import SlackHandler: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Error during test: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    print("=== SLACK INTEGRATION TEST ===\n")
    
    # Get list of users
    from django.contrib.auth import get_user_model
    User = get_user_model()
    users = User.objects.all()
    
    print(f"Available users ({users.count()}):")
    for i, user in enumerate(users, 1):
        display_name = user.username or user.email or f"User {user.id}"
        print(f"{i}. ID: {user.id}, Name: {display_name}")
    
    # Get user input
    user_input = input("\nSelect user number or ID (or press Enter to see users with Slack integration): ").strip()
    
    user_id = None
    if user_input:
        try:
            if user_input.isdigit() and 1 <= int(user_input) <= users.count():
                user_id = users[int(user_input) - 1].id
            else:
                user_id = int(user_input)
        except (ValueError, IndexError):
            print(f"Invalid input: {user_input}")
    
    # Get channel and message
    channel = input("\nEnter channel name (default: general): ").strip() or None
    message = input("Enter test message (default: Test message): ").strip() or None
    
    # Run test
    test_slack_integration(user_id, channel, message) 