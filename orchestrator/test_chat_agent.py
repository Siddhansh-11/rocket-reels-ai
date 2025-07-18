#!/usr/bin/env python3
"""Test script for the chat agent functionality"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from chat_agent import run_chat_agent, handle_direct_routing, MODEL_AVAILABLE, STORAGE_AVAILABLE

async def test_chat_agent():
    """Test various chat agent functionalities"""
    print("🧪 CHAT AGENT TEST SUITE")
    print("=" * 60)
    
    # Check system status
    print("\n📊 System Status:")
    print(f"- Model Available: {'✅' if MODEL_AVAILABLE else '❌'}")
    print(f"- Storage Available: {'✅' if STORAGE_AVAILABLE else '❌'}")
    
    # Test cases
    test_cases = [
        {
            "name": "Show Stored Articles",
            "message": "show stored articles",
            "expected": "STORED ARTICLES DATABASE"
        },
        {
            "name": "Search Request",
            "message": "search AI news",
            "expected": "SEARCH REQUEST DETECTED"
        },
        {
            "name": "Crawl Request",
            "message": "crawl https://example.com",
            "expected": "CRAWL REQUEST DETECTED"
        },
        {
            "name": "Script Generation",
            "message": "generate script",
            "expected": "SCRIPT GENERATION REQUEST"
        },
        {
            "name": "Check Database",
            "message": "check database status",
            "expected": "SCRIPTS TABLE ACCESS CHECK"
        },
        {
            "name": "Help Command",
            "message": "help",
            "expected": "Chat Agent"
        }
    ]
    
    print("\n🔄 Running Tests...")
    print("-" * 60)
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        print(f"\n📋 Test: {test['name']}")
        print(f"📨 Message: '{test['message']}'")
        
        try:
            # Run the chat agent
            response = await run_chat_agent(test['message'])
            
            # Check if expected text is in response
            if test['expected'] in response:
                print(f"✅ PASSED - Found '{test['expected']}'")
                passed += 1
            else:
                print(f"❌ FAILED - Expected '{test['expected']}' not found")
                print(f"📤 Response preview: {response[:150]}...")
                failed += 1
                
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            failed += 1
    
    # Test direct routing fallback
    print("\n\n🔀 Testing Direct Routing Fallback...")
    print("-" * 60)
    
    direct_test_cases = [
        "show stored articles",
        "search news",
        "help"
    ]
    
    for message in direct_test_cases:
        print(f"\n📨 Direct routing: '{message}'")
        try:
            response = handle_direct_routing(message)
            print(f"📤 Response preview: {response[:100]}...")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    # Summary
    print("\n\n📊 TEST SUMMARY")
    print("=" * 60)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Success Rate: {(passed/(passed+failed)*100):.1f}%" if (passed+failed) > 0 else "N/A")
    
    if failed == 0:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️ {failed} test(s) failed. Please check the implementation.")

async def interactive_test():
    """Interactive testing mode"""
    print("\n🤖 INTERACTIVE CHAT AGENT TEST")
    print("=" * 60)
    print("Type 'exit' to quit, 'help' for commands")
    print("-" * 60)
    
    while True:
        try:
            message = input("\n💬 You: ").strip()
            
            if message.lower() == 'exit':
                print("👋 Goodbye!")
                break
            
            print("\n🤖 Agent: ", end="", flush=True)
            response = await run_chat_agent(message)
            print(response)
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")

async def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test the chat agent")
    parser.add_argument("--interactive", "-i", action="store_true", 
                       help="Run in interactive mode")
    parser.add_argument("--message", "-m", type=str,
                       help="Test with a specific message")
    
    args = parser.parse_args()
    
    if args.message:
        # Test specific message
        print(f"\n📨 Testing message: '{args.message}'")
        response = await run_chat_agent(args.message)
        print(f"\n🤖 Response:\n{response}")
    elif args.interactive:
        # Interactive mode
        await interactive_test()
    else:
        # Run full test suite
        await test_chat_agent()

if __name__ == "__main__":
    asyncio.run(main())