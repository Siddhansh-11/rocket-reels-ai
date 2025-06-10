#!/usr/bin/env python3
"""
Health check script for Rocket Reels AI services
"""
import asyncio
import aiohttp
import sys
from typing import Dict, List

SERVICES = {
    "orchestrator": "http://localhost:8001",
    "input-processor": "http://localhost:8081",
    "research": "http://localhost:8082", 
    "planner": "http://localhost:8083",
    "script": "http://localhost:8084",
    "visual": "http://localhost:8085",  # Changed from visual-generator
    "assembly": "http://localhost:8086",
    "export": "http://localhost:8087",
    "distribution": "http://localhost:8088",
    "analytics": "http://localhost:8089"
}

async def check_service(session: aiohttp.ClientSession, name: str, url: str) -> Dict[str, str]:
    """Check if a service is healthy"""
    try:
        async with session.get(f"{url}/health", timeout=5) as response:
            if response.status == 200:
                return {"service": name, "status": "✅ HEALTHY", "url": url}
            else:
                return {"service": name, "status": f"❌ ERROR ({response.status})", "url": url}
    except asyncio.TimeoutError:
        return {"service": name, "status": "⏰ TIMEOUT", "url": url}
    except aiohttp.ClientConnectorError:
        return {"service": name, "status": "❌ CONNECTION_REFUSED", "url": url}
    except Exception as e:
        return {"service": name, "status": f"❌ FAILED ({str(e)[:30]})", "url": url}

async def check_docker_services():
    """Check Docker service status"""
    import subprocess
    try:
        result = subprocess.run(
            ["docker-compose", "ps", "--format", "table"],
            capture_output=True,
            text=True,
            cwd="."
        )
        
        if result.returncode == 0:
            print("🐳 Docker Services Status:")
            print(result.stdout)
        else:
            print("❌ Failed to get Docker status")
            print(result.stderr)
    except Exception as e:
        print(f"❌ Docker check failed: {e}")

async def main():
    """Run health checks for all services"""
    print("🏥 Rocket Reels AI - Health Check")
    print("=" * 50)
    
    # Check Docker services first
    await check_docker_services()
    print("\n" + "=" * 50)
    
    async with aiohttp.ClientSession() as session:
        tasks = [check_service(session, name, url) for name, url in SERVICES.items()]
        results = await asyncio.gather(*tasks)
        
        healthy_count = 0
        for result in results:
            print(f"{result['service']:20} {result['status']}")
            if "HEALTHY" in result["status"]:
                healthy_count += 1
        
        print("=" * 50)
        print(f"Services Healthy: {healthy_count}/{len(SERVICES)}")
        
        if healthy_count == len(SERVICES):
            print("🎉 All services are running correctly!")
            print("\n🚀 Ready to generate videos!")
            print("   Test workflow: python test_workflow.py")
            print("   Human Review: http://localhost:8000")
            print("   API Docs: http://localhost:8001/docs")
            return 0
        elif healthy_count > 0:
            print("⚠️  Some services are not healthy. Check Docker logs.")
            print("   Run: docker-compose logs [service-name]")
            print("\n💡 Tips:")
            print("   - Wait 30 seconds for services to fully start")
            print("   - Check .env file has required API keys")
            print("   - Ensure ports 8000-8089 are available")
            return 1
        else:
            print("❌ No services are responding.")
            print("   Run: docker-compose up -d")
            print("   Check: docker-compose logs")
            return 2

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)