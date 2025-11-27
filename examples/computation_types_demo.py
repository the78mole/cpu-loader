#!/usr/bin/env python3
"""
Demonstration script for different computation types in cpu-loader.

This script shows how to use different computation algorithms for CPU load generation:
- busy-wait: Simple busy loop (fastest, minimal computation)
- pi: PI calculation using Leibniz formula
- primes: Prime number finding algorithms
- matrix: 4x4 matrix multiplication
- fibonacci: Recursive Fibonacci calculation (most CPU intensive)

Usage:
    python examples/computation_types_demo.py
"""

import time
import requests
import json
import argparse

API_BASE = "http://localhost:8000"

def get_computation_type():
    """Get current computation type."""
    try:
        response = requests.get(f"{API_BASE}/api/computation-type")
        if response.status_code == 200:
            data = response.json()
            return data['computation_type'], data['available_types']
        else:
            print(f"Error getting computation type: {response.status_code}")
            return None, None
    except requests.RequestException as e:
        print(f"Error connecting to API: {e}")
        return None, None

def set_computation_type(comp_type):
    """Set computation type."""
    try:
        response = requests.put(
            f"{API_BASE}/api/computation-type",
            headers={'Content-Type': 'application/json'},
            data=json.dumps({'computation_type': comp_type})
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {data['message']}")
            return True
        else:
            print(f"Error setting computation type: {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"Error connecting to API: {e}")
        return False

def set_load(load_percent):
    """Set load for all threads."""
    try:
        response = requests.post(
            f"{API_BASE}/api/threads/load/all",
            headers={'Content-Type': 'application/json'},
            data=json.dumps({'load_percent': load_percent})
        )
        if response.status_code == 200:
            data = response.json()
            print(f"🔥 Load set to {load_percent}% across {data['num_threads']} threads")
            return True
        else:
            print(f"Error setting load: {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"Error connecting to API: {e}")
        return False

def get_cpu_metrics():
    """Get current CPU metrics."""
    try:
        response = requests.get(f"{API_BASE}/api/cpu-metrics")
        if response.status_code == 200:
            data = response.json()
            return data['total_cpu_percent'], data['per_cpu_percent']
        else:
            return None, None
    except requests.RequestException as e:
        return None, None

def demo_computation_type(comp_type, description, load_percent=50, duration=10):
    """Demonstrate a specific computation type."""
    print(f"\n{'='*60}")
    print(f"🧮 Testing: {comp_type.upper()}")
    print(f"📝 Description: {description}")
    print(f"⚡ Load: {load_percent}%")
    print(f"⏱️  Duration: {duration}s")
    print(f"{'='*60}")

    # Set computation type
    if not set_computation_type(comp_type):
        return

    # Set load
    if not set_load(load_percent):
        return

    # Monitor for specified duration
    print("📊 Monitoring CPU usage...")
    start_time = time.time()
    cpu_readings = []

    while time.time() - start_time < duration:
        total_cpu, per_cpu = get_cpu_metrics()
        if total_cpu is not None:
            cpu_readings.append(total_cpu)
            print(f"  CPU: {total_cpu:5.1f}% | Per-core: {[f'{cpu:4.1f}' for cpu in per_cpu[:4]]}")
        time.sleep(1)

    # Calculate statistics
    if cpu_readings:
        avg_cpu = sum(cpu_readings) / len(cpu_readings)
        max_cpu = max(cpu_readings)
        min_cpu = min(cpu_readings)
        print(f"\n📈 Results for {comp_type}:")
        print(f"  Average CPU: {avg_cpu:.1f}%")
        print(f"  Max CPU: {max_cpu:.1f}%")
        print(f"  Min CPU: {min_cpu:.1f}%")

    # Reset load
    set_load(0)

def main():
    parser = argparse.ArgumentParser(description='Demonstrate CPU loader computation types')
    parser.add_argument('--load', type=int, default=75,
                       help='Load percentage to test (default: 75)')
    parser.add_argument('--duration', type=int, default=8,
                       help='Test duration in seconds per computation type (default: 8)')
    parser.add_argument('--types', nargs='+',
                       choices=['busy-wait', 'pi', 'primes', 'matrix', 'fibonacci'],
                       help='Specific computation types to test (default: all)')
    args = parser.parse_args()

    print("🚀 CPU Loader Computation Types Demo")
    print("====================================")

    # Check if API is available
    current_type, available_types = get_computation_type()
    if current_type is None:
        print("❌ Error: Cannot connect to cpu-loader API")
        print("   Make sure cpu-loader is running on http://localhost:8000")
        print("   Start it with: uv run cpu-loader")
        return

    print(f"🔗 Connected to cpu-loader API")
    print(f"📋 Available computation types: {', '.join(available_types)}")
    print(f"🎯 Current type: {current_type}")

    # Define computation types with descriptions
    computation_demos = [
        ("busy-wait", "Simple busy loop - fastest execution, minimal computation overhead"),
        ("pi", "PI calculation using Leibniz formula - moderate computational intensity"),
        ("primes", "Prime number finding - variable computational load"),
        ("matrix", "4x4 matrix multiplication - consistent computational patterns"),
        ("fibonacci", "Recursive Fibonacci calculation - highest computational intensity"),
    ]

    # Filter if specific types requested
    if args.types:
        computation_demos = [(ct, desc) for ct, desc in computation_demos if ct in args.types]

    # Run demonstrations
    for comp_type, description in computation_demos:
        demo_computation_type(comp_type, description, args.load, args.duration)
        time.sleep(2)  # Brief pause between tests

    print(f"\n✅ Demo completed! All computation types tested.")
    print("💡 Observations:")
    print("  - busy-wait: Lowest CPU overhead, most predictable timing")
    print("  - pi: Good balance of computation and performance")
    print("  - primes: Variable load based on number ranges")
    print("  - matrix: Consistent computational patterns")
    print("  - fibonacci: Highest CPU intensity, may show different characteristics")

if __name__ == "__main__":
    main()
