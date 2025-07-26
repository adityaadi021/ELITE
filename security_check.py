#!/usr/bin/env python3
"""
Security Check Script
Checks for exposed tokens or sensitive data in the codebase
"""

import os
import re
import json

def check_for_exposed_tokens():
    """Check for exposed tokens in the codebase"""
    print("🔒 Running Security Check...")
    
    # Files to check
    files_to_check = [
        'bot.py',
        'config.json',
        'README.md'
    ]
    
    # Patterns that might indicate exposed tokens
    patterns = [
        r'[A-Za-z0-9]{23,28}\.[\w-]{6,7}\.[\w-]{27}',  # Discord token pattern
        r'token["\']?\s*[:=]\s*["\'][^"\']{20,}["\']',  # Token assignments with actual tokens
    ]
    
    issues_found = []
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for pattern in patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        issues_found.append({
                            'file': file_path,
                            'pattern': pattern,
                            'matches': matches
                        })
            except Exception as e:
                print(f"⚠️  Could not read {file_path}: {e}")
    
    # Check config.json specifically
    if os.path.exists('config.json'):
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
            
            token = config.get('token', '')
            if token and token != "YOUR_BOT_TOKEN_HERE" and len(token) > 20:
                issues_found.append({
                    'file': 'config.json',
                    'pattern': 'Actual token found',
                    'matches': [f'Token: {token[:10]}...']
                })
        except Exception as e:
            print(f"⚠️  Could not read config.json: {e}")
    
    # Report results
    if issues_found:
        print("❌ Security Issues Found:")
        for issue in issues_found:
            print(f"   📁 {issue['file']}")
            print(f"   🔍 Pattern: {issue['pattern']}")
            for match in issue['matches'][:3]:  # Show first 3 matches
                print(f"      - {match}")
            if len(issue['matches']) > 3:
                print(f"      ... and {len(issue['matches']) - 3} more")
            print()
    else:
        print("✅ No exposed tokens found!")
    
    # Check environment variables
    env_token = os.getenv('TOKEN')
    if env_token:
        print("✅ TOKEN environment variable is set")
    else:
        print("⚠️  TOKEN environment variable not set")
    
    # Check for placeholder text (this is good)
    print("\n📝 Configuration Status:")
    if os.path.exists('config.json'):
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
            token = config.get('token', '')
            if token == "YOUR_BOT_TOKEN_HERE":
                print("✅ config.json has placeholder (safe)")
            elif token and len(token) > 20:
                print("⚠️  config.json has actual token (should use env vars for production)")
            else:
                print("⚠️  config.json token not set")
        except:
            print("❌ Could not read config.json")
    
    print("\n🔒 Security Check Complete!")

if __name__ == "__main__":
    check_for_exposed_tokens() 