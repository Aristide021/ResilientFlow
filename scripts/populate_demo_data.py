
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def populate_demo_data():
    '''Populate the command center with demo workflow data'''
    from orchestrator import handle_disaster_event
    
    demo_incidents = [
        {
            "event_type": "hurricane",
            "severity": 85,
            "location": "Miami, FL",
            "latitude": 25.7617,
            "longitude": -80.1918,
            "affected_population": 450000
        },
        {
            "event_type": "wildfire", 
            "severity": 92,
            "location": "Los Angeles, CA",
            "latitude": 34.0522,
            "longitude": -118.2437,
            "affected_population": 75000
        },
        {
            "event_type": "earthquake",
            "severity": 78,
            "location": "San Francisco, CA", 
            "latitude": 37.7749,
            "longitude": -122.4194,
            "affected_population": 125000
        }
    ]
    
    print("Populating Command Center with demo data...")
    
    for i, incident in enumerate(demo_incidents, 1):
        print(f"Processing incident {i}/3: {incident['event_type']} in {incident['location']}")
        
        incident["event_id"] = f"demo_{incident['event_type']}_{i}"
        incident["timestamp"] = datetime.now().isoformat()
        incident["satellite_image"] = f"mock_{incident['event_type']}_data.tiff"
        
        try:
            result = await handle_disaster_event(incident)
            print(f"Completed: {result.get('resources_allocated', 0)} resources, {result.get('alerts_sent', 0)} alerts")
        except Exception as e:
            print(f"Failed: {e}")
    
    print("Demo data population complete!")

if __name__ == "__main__":
    from datetime import datetime
    asyncio.run(populate_demo_data())
