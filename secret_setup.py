#!/usr/bin/env python3
"""
OperatorOS Secret Key Setup
Automated setup wizard for new deployments
"""

import os
import sys
import getpass
import re
from typing import Dict, Optional

class SecretKeySetup:
    """Setup wizard for OperatorOS secret keys"""
    
    def __init__(self):
        self.required_secrets = {
            'OPENAI_API_KEY': {
                'name': 'OpenAI API Key',
                'description': 'Required for OpenAI GPT models',
                'pattern': r'^sk-[a-zA-Z0-9]{20,}$',
                'url': 'https://platform.openai.com/api-keys',
                'example': 'sk-proj-...'
            },
            'ANTHROPIC_API_KEY': {
                'name': 'Anthropic API Key',
                'description': 'Required for Claude models',
                'pattern': r'^sk-ant-[a-zA-Z0-9\-]{20,}$',
                'url': 'https://console.anthropic.com/keys',
                'example': 'sk-ant-api03-...'
            },
            'GEMINI_API_KEY': {
                'name': 'Google Gemini API Key',
                'description': 'Required for Gemini models',
                'pattern': r'^[a-zA-Z0-9\-_]{30,}$',
                'url': 'https://makersuite.google.com/app/apikey',
                'example': 'AIzaSy...'
            },
            'DATABASE_URL': {
                'name': 'Database Connection URL',
                'description': 'PostgreSQL database connection string',
                'pattern': r'^postgres(ql)?://.*$',
                'url': 'https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING',
                'example': 'postgresql://user:password@localhost:5432/database'
            },
            'SESSION_SECRET': {
                'name': 'Session Secret Key',
                'description': 'Secret key for session encryption',
                'pattern': r'^.{32,}$',
                'url': None,
                'example': 'auto-generated-32-character-string'
            }
        }
        
    def check_existing_secrets(self) -> Dict[str, bool]:
        """Check which secrets are already configured"""
        status = {}
        for key in self.required_secrets.keys():
            status[key] = bool(os.environ.get(key))
        return status
    
    def validate_secret(self, key: str, value: str) -> bool:
        """Validate secret key format"""
        if not value or not value.strip():
            return False
            
        config = self.required_secrets[key]
        pattern = config['pattern']
        
        return bool(re.match(pattern, value.strip()))
    
    def generate_session_secret(self) -> str:
        """Generate a secure session secret"""
        import secrets
        import string
        
        alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
        return ''.join(secrets.choice(alphabet) for _ in range(32))
    
    def prompt_for_secret(self, key: str) -> Optional[str]:
        """Prompt user for a specific secret key"""
        config = self.required_secrets[key]
        
        print(f"\n{'='*60}")
        print(f"🔑 {config['name']}")
        print(f"{'='*60}")
        print(f"Description: {config['description']}")
        
        if config['url']:
            print(f"Get your key at: {config['url']}")
        
        print(f"Format example: {config['example']}")
        
        if key == 'SESSION_SECRET':
            print("\nPress Enter to auto-generate a secure session secret, or provide your own:")
            
        while True:
            try:
                if key == 'SESSION_SECRET':
                    value = input("Enter session secret (or press Enter for auto-generate): ").strip()
                    if not value:
                        value = self.generate_session_secret()
                        print(f"✓ Auto-generated session secret (32 characters)")
                        return value
                else:
                    value = getpass.getpass(f"Enter {config['name']}: ").strip()
                
                if not value:
                    print("❌ Secret cannot be empty. Please try again.")
                    continue
                
                if self.validate_secret(key, value):
                    print(f"✓ Valid {config['name']} format")
                    return value
                else:
                    print(f"❌ Invalid format for {config['name']}. Please check the example and try again.")
                    
            except KeyboardInterrupt:
                print("\n\nSetup cancelled by user.")
                return None
            except Exception as e:
                print(f"❌ Error: {e}")
                continue
    
    def setup_environment_file(self, secrets: Dict[str, str]) -> bool:
        """Create or update .env file with secrets"""
        try:
            env_content = []
            
            # Add header
            env_content.append("# OperatorOS Environment Configuration")
            env_content.append("# Generated automatically by secret setup wizard")
            env_content.append("")
            
            # Add secrets
            for key, value in secrets.items():
                env_content.append(f"{key}={value}")
            
            # Add default configurations
            env_content.extend([
                "",
                "# Default Configuration",
                "FLASK_ENV=production",
                "DEFAULT_API_PROVIDER=openai",
                "OPENAI_MODEL=gpt-4o",
                "ANTHROPIC_MODEL=claude-sonnet-4-20250514",
                "GEMINI_MODEL=gemini-2.5-flash",
                "RATELIMIT_DEFAULT=10 per minute",
                "MAX_CONVERSATION_LENGTH=10",
                "MAX_INPUT_LENGTH=5000",
                "LOG_LEVEL=INFO"
            ])
            
            with open('.env', 'w') as f:
                f.write('\n'.join(env_content))
            
            print(f"✓ Environment file created: .env")
            return True
            
        except Exception as e:
            print(f"❌ Error creating .env file: {e}")
            return False
    
    def run_setup(self) -> bool:
        """Run the complete setup wizard"""
        print("🚀 OperatorOS Secret Key Setup Wizard")
        print("=" * 60)
        
        # Check existing secrets
        existing = self.check_existing_secrets()
        configured_count = sum(existing.values())
        
        if configured_count == len(self.required_secrets):
            print("✅ All required secrets are already configured!")
            response = input("Do you want to reconfigure them? (y/N): ").strip().lower()
            if response != 'y':
                return True
        
        print(f"Found {configured_count}/{len(self.required_secrets)} secrets configured")
        print("\nStarting setup process...")
        
        secrets = {}
        
        # Prompt for each required secret
        for key in self.required_secrets.keys():
            if existing.get(key, False):
                print(f"\n✓ {key} already configured")
                response = input(f"Reconfigure {key}? (y/N): ").strip().lower()
                if response != 'y':
                    secrets[key] = os.environ.get(key)
                    continue
            
            value = self.prompt_for_secret(key)
            if value is None:
                print("❌ Setup cancelled")
                return False
            
            secrets[key] = value
        
        # Create environment file
        if self.setup_environment_file(secrets):
            print("\n" + "=" * 60)
            print("🎉 Setup completed successfully!")
            print("=" * 60)
            print("Next steps:")
            print("1. Restart your application to load the new environment variables")
            print("2. Test your OperatorOS deployment")
            print("3. Access the system at http://localhost:5000")
            print("\n⚠️  Security reminder: Never commit your .env file to version control!")
            return True
        
        return False

def main():
    """Main entry point for secret setup"""
    setup = SecretKeySetup()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--check':
        # Check mode - just show status
        existing = setup.check_existing_secrets()
        print("Secret Key Status:")
        for key, configured in existing.items():
            status = "✅ Configured" if configured else "❌ Missing"
            print(f"  {key}: {status}")
        return
    
    # Run full setup
    success = setup.run_setup()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()