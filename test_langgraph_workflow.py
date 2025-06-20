#!/usr/bin/env python3
"""
Test script for LangGraph workflow orchestration
Run this after starting all services with docker-compose
"""

import asyncio
import json
import os
import sys
from typing import Dict, Any, Optional
import logging
from pathlib import Path

# Add orchestrator to path
sys.path.append(str(Path(__file__).parent / "orchestrator"))

from dotenv import load_dotenv
from langchain_core.runnables.config import RunnableConfig

# Load environment variables
load_dotenv('.env')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WorkflowTester:
    """Test harness for the LangGraph workflow"""
    
    def __init__(self):
        self.config_path = Path(__file__).parent / "langgraph.json"
        self.load_config()
        
    def load_config(self):
        """Load langgraph.json configuration"""
        with open(self.config_path, 'r') as f:
            self.config = json.load(f)
        logger.info(f"Loaded configuration from {self.config_path}")
    
    async def test_mcp_connectivity(self) -> Dict[str, bool]:
        """Test connectivity to all MCP servers"""
        import aiohttp
        results = {}
        
        for server_name, server_config in self.config["dev"]["mcp_servers"].items():
            url = server_config["url"]
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{url}/health", timeout=5) as response:
                        results[server_name] = response.status == 200
                        logger.info(f"✅ {server_name} is reachable at {url}")
            except Exception as e:
                results[server_name] = False
                logger.error(f"❌ {server_name} is not reachable at {url}: {e}")
        
        return results
    
    async def test_workflow_initialization(self):
        """Test workflow graph initialization"""
        try:
            from langraph_workflow import create_workflow, ContentState
            
            # Create workflow
            workflow = create_workflow()
            logger.info("✅ Workflow graph created successfully")
            
            # Test initial state
            test_state = ContentState(
                workflow_id="test-123",
                input_type="prompt",
                input_data={"prompt": "Test prompt", "style": "educational"}
            )
            logger.info("✅ Initial state created successfully")
            
            # Compile workflow
            app = workflow.compile()
            logger.info("✅ Workflow compiled successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Workflow initialization failed: {e}")
            return False
    
    async def test_simple_workflow(self, auto_approve: bool = False):
        """Run a simple test workflow"""
        try:
            from langraph_workflow import run_workflow
            
            # Use test input from config
            test_input = self.config["dev"]["test_inputs"][0]
            
            logger.info(f"Starting test workflow with input: {test_input}")
            
            if auto_approve:
                # Set environment variable for auto-approval
                os.environ["AUTO_APPROVE_REVIEWS"] = "true"
            
            # Run workflow
            result = await run_workflow(
                input_type=test_input["input_type"],
                input_data=test_input["input_data"]
            )
            
            logger.info(f"✅ Workflow completed successfully")
            logger.info(f"   Workflow ID: {result.workflow_id}")
            logger.info(f"   Total Cost: ${result.total_cost_usd:.2f}")
            logger.info(f"   Phases Completed: {result.phases_completed}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Workflow execution failed: {e}")
            raise
    
    async def test_state_persistence(self):
        """Test workflow state persistence and recovery"""
        try:
            from langraph_workflow import ContentState
            
            # Create test state
            state = ContentState(
                workflow_id="persist-test-123",
                input_type="prompt",
                input_data={"prompt": "Test persistence"}
            )
            
            # Convert to checkpoint
            checkpoint = state.to_checkpoint()
            logger.info("✅ State serialized to checkpoint")
            
            # Restore from checkpoint
            restored = ContentState.from_checkpoint(checkpoint)
            logger.info("✅ State restored from checkpoint")
            
            # Verify
            assert restored.workflow_id == state.workflow_id
            assert restored.input_type == state.input_type
            
            return True
            
        except Exception as e:
            logger.error(f"❌ State persistence test failed: {e}")
            return False
    
    async def test_error_handling(self):
        """Test workflow error handling"""
        try:
            from langraph_workflow import run_workflow
            
            # Test with invalid input
            logger.info("Testing error handling with invalid input...")
            
            try:
                result = await run_workflow(
                    input_type="invalid_type",
                    input_data={}
                )
            except Exception as e:
                logger.info(f"✅ Error handled correctly: {e}")
                return True
            
            logger.error("❌ Expected error was not raised")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error handling test failed: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all workflow tests"""
        logger.info("🚀 Starting LangGraph Workflow Tests")
        logger.info("=" * 50)
        
        # Test 1: MCP Connectivity
        logger.info("\n📡 Test 1: MCP Server Connectivity")
        mcp_results = await self.test_mcp_connectivity()
        all_connected = all(mcp_results.values())
        
        if not all_connected:
            logger.warning("⚠️  Some MCP servers are not reachable. Make sure docker-compose is running!")
            logger.info("Run: docker-compose up -d")
            return
        
        # Test 2: Workflow Initialization
        logger.info("\n🔧 Test 2: Workflow Initialization")
        init_success = await self.test_workflow_initialization()
        
        if not init_success:
            logger.error("Workflow initialization failed. Cannot proceed with further tests.")
            return
        
        # Test 3: State Persistence
        logger.info("\n💾 Test 3: State Persistence")
        persist_success = await self.test_state_persistence()
        
        # Test 4: Error Handling
        logger.info("\n🛡️  Test 4: Error Handling")
        error_success = await self.test_error_handling()
        
        # Test 5: Simple Workflow (Auto-approved)
        logger.info("\n🎬 Test 5: Simple Workflow Execution (Auto-approved)")
        try:
            workflow_result = await self.test_simple_workflow(auto_approve=True)
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
        
        # Summary
        logger.info("\n" + "=" * 50)
        logger.info("📊 Test Summary:")
        logger.info(f"   MCP Connectivity: {'✅' if all_connected else '❌'}")
        logger.info(f"   Workflow Init: {'✅' if init_success else '❌'}")
        logger.info(f"   State Persistence: {'✅' if persist_success else '❌'}")
        logger.info(f"   Error Handling: {'✅' if error_success else '❌'}")
        
        logger.info("\n📝 Next Steps:")
        logger.info("1. Access human review interface: http://localhost:8000")
        logger.info("2. Monitor in LangGraph Studio: https://smith.langchain.com/projects")
        logger.info("3. Run manual workflow: python test_workflow.py")

async def main():
    """Main test runner"""
    tester = WorkflowTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())