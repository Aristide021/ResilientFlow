"""
Test ADK Setup for ResilientFlow
"""

import asyncio
from typing import Dict, Any

# Test ADK import
try:
    from google.adk.agents import Agent
    print("✅ ADK Agent imported successfully")
except ImportError as e:
    print(f"❌ Failed to import ADK Agent: {e}")
    exit(1)

# Simple test tool
def test_tool(message: str) -> str:
    """Simple test tool for ADK demonstration"""
    return f"Test tool received: {message}"

# Create test agent
try:
    test_agent = Agent(
        name="test_agent",
        model="gemini-2.0-flash",
        description="A simple test agent for ResilientFlow",
        instruction="You are a test agent. Use the test_tool when asked to test something.",
        tools=[test_tool]
    )
    print("✅ Test agent created successfully")
    print(f"Agent name: {test_agent.name}")
    print(f"Agent model: {test_agent.model}")
except Exception as e:
    print(f"❌ Failed to create test agent: {e}")
    exit(1)

print("🎉 ADK setup validation completed successfully!")
print("✅ ResilientFlow is ready to use the Agent Development Kit") 