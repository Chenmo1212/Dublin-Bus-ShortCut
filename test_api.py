"""
Simple test script to verify the API works
Run with: python test_api.py
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_root():
    """Test the root endpoint"""
    print("\n=== Testing Root Endpoint ===")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_best_route_to_home():
    """Test the best route to home endpoint"""
    print("\n=== Testing Best Route To Home ===")
    try:
        response = requests.get(f"{BASE_URL}/best-route/to-home", timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Success!")
            print(f"Response: {json.dumps(data, indent=2)}")
            
            # Print human-readable summary
            if data.get("success"):
                rec = data.get("recommendation", {})
                print(f"\n📍 Recommended Route:")
                print(f"   🚌 Take {rec['e_bus']['service']} at {rec['e_bus']['departure_time']}")
                print(f"   📍 Arrive Westmoreland at {rec['westmoreland_arrival']['time']}")
                print(f"   🚶 Walk 6 minutes to Eden Quay")
                print(f"   📍 Arrive Eden Quay at {rec['eden_quay_arrival']['time']}")
                print(f"   ⏱️  Wait {rec['wait_minutes']} minutes")
                print(f"   🚌 Take Bus 15 at {rec['bus_15']['departure_time']} to {rec['bus_15']['destination']}")
                print(f"   ⏱️  Total journey: {rec['total_journey_minutes']} minutes")
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out (API might be slow)")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("=" * 60)
    print("Dublin Bus Route Optimizer - API Test")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Test root endpoint
    root_ok = test_root()
    
    # Test best route endpoint
    route_ok = test_best_route_to_home()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print(f"  Root endpoint: {'✅ PASS' if root_ok else '❌ FAIL'}")
    print(f"  Best route endpoint: {'✅ PASS' if route_ok else '❌ FAIL'}")
    print("=" * 60)
    
    if root_ok and route_ok:
        print("\n🎉 All tests passed!")
        print("\nYou can now use this API with iOS Shortcuts:")
        print(f"  URL: {BASE_URL}/best-route/to-home")
    else:
        print("\n⚠️  Some tests failed. Check the output above.")

if __name__ == "__main__":
    main()

# Made with Bob
