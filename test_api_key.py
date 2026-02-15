import httpx
import asyncio
from app.config import settings

async def test_key():
    print(f"Testing API Key: {settings.rapidapi_key[:20]}...")
    
    url = "https://real-time-glassdoor-data.p.rapidapi.com/reviews"
    
    headers = {
        "X-RapidAPI-Key": settings.rapidapi_key,
        "X-RapidAPI-Host": "real-time-glassdoor-data.p.rapidapi.com"
    }
    
    params = {"company_name": "NVIDIA", "limit": 5}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        
        if response.status_code == 200:
            print("✅ API Key works!")
            data = response.json()
            print(f"Reviews found: {len(data.get('reviews', []))}")
        else:
            print(f"❌ Error: {response.status_code}")

asyncio.run(test_key())
