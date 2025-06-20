from setuptools import setup, find_packages

setup(
    name="rocket-reels-orchestrator",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "langgraph>=0.2.0",
        "langchain>=0.1.0",
        "langchain-anthropic>=0.1.0",
        "mcp>=0.1.0",
        "pydantic>=2.0.0",
        "fastapi>=0.100.0",
        "uvicorn>=0.23.0",
        "websockets>=11.0",
        "aiofiles>=23.0",
        "supabase>=2.0.0",
        "python-dotenv>=1.0.0",
        "langgraph-checkpoint>=1.0.0",
    ],
)