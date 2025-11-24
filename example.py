#!/usr/bin/env python3
"""
Example script demonstrating programmatic control of CPU loader via REST API.
Make sure the CPU loader server is running before executing this script.
"""
import requests
import time

BASE_URL = "http://localhost:8000/api"


def get_status():
    """Get current thread status."""
    response = requests.get(f"{BASE_URL}/threads")
    return response.json()


def set_all_threads(load_percent):
    """Set load for all threads."""
    response = requests.post(
        f"{BASE_URL}/threads/load/all",
        json={"load_percent": load_percent}
    )
    return response.json()


def set_thread(thread_id, load_percent):
    """Set load for a specific thread."""
    response = requests.put(
        f"{BASE_URL}/threads/{thread_id}/load",
        json={"load_percent": load_percent}
    )
    return response.json()


def main():
    """Run example scenarios."""
    print("CPU Loader API Example")
    print("=" * 50)
    
    # Get initial status
    print("\n1. Getting initial status...")
    status = get_status()
    print(f"   Active threads: {status['num_threads']}")
    print(f"   Loads: {status['loads']}")
    
    # Set all threads to 25%
    print("\n2. Setting all threads to 25%...")
    result = set_all_threads(25)
    print(f"   {result['message']}")
    time.sleep(2)
    
    # Gradually increase load
    print("\n3. Gradually increasing load...")
    for load in [25, 50, 75, 100]:
        print(f"   Setting to {load}%...")
        set_all_threads(load)
        time.sleep(3)
    
    # Individual thread control
    print("\n4. Individual thread control...")
    num_threads = get_status()['num_threads']
    for i in range(num_threads):
        load = (i + 1) * 25  # 25%, 50%, 75%, 100%
        print(f"   Thread {i}: {load}%")
        set_thread(i, load)
        time.sleep(1)
    
    time.sleep(3)
    
    # Reset to idle
    print("\n5. Resetting to idle (0%)...")
    set_all_threads(0)
    final_status = get_status()
    print(f"   Final loads: {final_status['loads']}")
    
    print("\n✅ Example completed!")


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("❌ Error: Cannot connect to CPU loader server.")
        print("   Please start the server first: python main.py")
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
