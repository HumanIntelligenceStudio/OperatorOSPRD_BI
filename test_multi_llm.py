#!/usr/bin/env python3
"""
Direct Multi-LLM Provider Test Script
Tests all LLM providers independently to prove they work as designed
"""

import os
import sys
import logging
from multi_llm_provider import multi_llm, LLMProvider

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_provider_initialization():
    """Test that all providers are properly initialized"""
    print("🔧 Testing Provider Initialization")
    print("=" * 50)
    
    status = multi_llm.get_provider_status()
    
    print(f"Available Providers: {status['available_providers']}")
    print(f"Total Providers: {status['total_providers']}")
    print("\nModel Mappings:")
    for provider, model in status['model_mappings'].items():
        print(f"  {provider}: {model}")
    
    print("\nInitialization Status:")
    for provider, initialized in status['initialization_status'].items():
        status_icon = "✅" if initialized else "❌"
        print(f"  {status_icon} {provider.upper()}: {'Initialized' if initialized else 'Failed'}")
    
    return status['available_providers']

def test_individual_providers(available_providers):
    """Test each provider individually"""
    print("\n🧪 Testing Individual Providers")
    print("=" * 50)
    
    test_messages = [
        {
            "role": "system",
            "content": "You are an OperatorOS agent. Respond with precision and clarity. No flattery."
        },
        {
            "role": "user",
            "content": "Test response: Confirm your model and provider are working correctly. Be concise and precise."
        }
    ]
    
    results = {}
    
    for provider_name in available_providers:
        try:
            provider = LLMProvider(provider_name)
            print(f"\n🔍 Testing {provider_name.upper()}...")
            
            response = multi_llm.generate_response(
                messages=test_messages,
                provider=provider,
                max_tokens=150,
                temperature=0.3
            )
            
            if response.success:
                print(f"✅ {provider_name.upper()} SUCCESS")
                print(f"   Model: {response.model}")
                print(f"   Usage: {response.usage}")
                print(f"   Response: {response.content[:100]}{'...' if len(response.content) > 100 else ''}")
                results[provider_name] = "SUCCESS"
            else:
                print(f"❌ {provider_name.upper()} FAILED")
                print(f"   Error: {response.error}")
                results[provider_name] = f"FAILED: {response.error}"
                
        except Exception as e:
            print(f"💥 {provider_name.upper()} EXCEPTION: {str(e)}")
            results[provider_name] = f"EXCEPTION: {str(e)}"
    
    return results

def test_failover_mechanism():
    """Test automatic failover between providers"""
    print("\n🔄 Testing Failover Mechanism")
    print("=" * 50)
    
    # Test with a standard prompt to see which provider responds
    messages = [
        {
            "role": "system",
            "content": "You are an OperatorOS agent following production memory guidelines."
        },
        {
            "role": "user",
            "content": "Failover test: Which provider and model are you using?"
        }
    ]
    
    try:
        response = multi_llm.generate_response(
            messages=messages,
            provider=None,  # Let system choose
            max_tokens=100,
            temperature=0.5
        )
        
        if response.success:
            print(f"✅ FAILOVER SUCCESS")
            print(f"   Auto-selected Provider: {response.provider.value}")
            print(f"   Model: {response.model}")
            print(f"   Response: {response.content}")
        else:
            print(f"❌ FAILOVER FAILED: {response.error}")
    
    except Exception as e:
        print(f"💥 FAILOVER EXCEPTION: {str(e)}")

def test_all_providers_comprehensive():
    """Test all providers using the built-in test method"""
    print("\n🚀 Running Comprehensive Provider Test")
    print("=" * 50)
    
    try:
        results = multi_llm.test_all_providers()
        
        for provider, response in results.items():
            print(f"\n{provider.upper()}: {'✅ SUCCESS' if response.success else '❌ FAILED'}")
            print(f"  Model: {response.model}")
            if response.success:
                print(f"  Usage: {response.usage}")
                print(f"  Response: {response.content[:100]}{'...' if len(response.content) > 100 else ''}")
            else:
                print(f"  Error: {response.error}")
        
        return results
    
    except Exception as e:
        print(f"💥 COMPREHENSIVE TEST EXCEPTION: {str(e)}")
        return {}

def test_production_memory_compliance():
    """Test that responses follow OperatorOS production memory guidelines"""
    print("\n📋 Testing Production Memory Compliance")
    print("=" * 50)
    
    test_prompt = """
    Provide feedback on this statement: "You're doing amazing! This is incredible work and you should feel proud!"
    
    Respond according to OperatorOS production memory guidelines.
    """
    
    messages = [
        {
            "role": "system",
            "content": "You are an OperatorOS agent. Follow production memory guidelines: no flattery, no soothing, no inflation. Challenge with precision, not friction."
        },
        {
            "role": "user",
            "content": test_prompt
        }
    ]
    
    try:
        response = multi_llm.generate_response(
            messages=messages,
            provider=None,
            max_tokens=200,
            temperature=0.4
        )
        
        if response.success:
            print(f"✅ COMPLIANCE TEST SUCCESS")
            print(f"   Provider: {response.provider.value}")
            print(f"   Response: {response.content}")
            
            # Check for compliance indicators
            content_lower = response.content.lower()
            has_flattery = any(word in content_lower for word in ['amazing', 'incredible', 'proud', 'great job'])
            has_precision = any(word in content_lower for word in ['reflect', 'mirror', 'clarity', 'precise'])
            
            print(f"\n   Compliance Analysis:")
            print(f"   Contains flattery: {'❌ YES' if has_flattery else '✅ NO'}")
            print(f"   Contains precision language: {'✅ YES' if has_precision else '❌ NO'}")
        else:
            print(f"❌ COMPLIANCE TEST FAILED: {response.error}")
    
    except Exception as e:
        print(f"💥 COMPLIANCE TEST EXCEPTION: {str(e)}")

def main():
    """Run comprehensive multi-LLM test suite"""
    print("🎯 OperatorOS Multi-LLM Provider Test Suite")
    print("=" * 60)
    
    # Test 1: Provider Initialization
    available_providers = test_provider_initialization()
    
    if not available_providers:
        print("❌ NO PROVIDERS AVAILABLE - Check API keys")
        return False
    
    # Test 2: Individual Provider Tests
    individual_results = test_individual_providers(available_providers)
    
    # Test 3: Failover Mechanism
    test_failover_mechanism()
    
    # Test 4: Comprehensive Test
    comprehensive_results = test_all_providers_comprehensive()
    
    # Test 5: Production Memory Compliance
    test_production_memory_compliance()
    
    # Final Summary
    print("\n📊 FINAL TEST SUMMARY")
    print("=" * 50)
    
    success_count = sum(1 for result in individual_results.values() if result == "SUCCESS")
    total_providers = len(available_providers)
    
    print(f"Providers Tested: {total_providers}")
    print(f"Successful: {success_count}")
    print(f"Success Rate: {(success_count/total_providers)*100:.1f}%")
    
    for provider, result in individual_results.items():
        status_icon = "✅" if result == "SUCCESS" else "❌"
        print(f"{status_icon} {provider.upper()}: {result}")
    
    if success_count == total_providers:
        print("\n🎉 ALL PROVIDERS WORKING AS DESIGNED")
        return True
    else:
        print(f"\n⚠️ {total_providers - success_count} PROVIDER(S) NEED ATTENTION")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)