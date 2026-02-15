#!/usr/bin/env python3
"""
Test script to send recipe steps to receiver_jetson_full.py

Usage:
    python3 test_recipe_send.py [host] [port]

Example:
    python3 test_recipe_send.py localhost 9005
    python3 test_recipe_send.py 100.71.232.77 9005
"""

import json
import socket
import struct
import sys

def send_recipe(host, port, recipe_steps):
    """Send recipe steps to the receiver using length-prefixed TCP protocol."""
    print(f"Connecting to {host}:{port}...")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)

    try:
        sock.connect((host, port))
        print(f"Connected to {host}:{port}")

        # Encode recipe steps as JSON
        payload = json.dumps(recipe_steps).encode('utf-8')
        print(f"Sending {len(recipe_steps)} steps ({len(payload)} bytes)")

        # Create 4-byte big-endian length header
        header = struct.pack('>I', len(payload))

        # Send header + payload
        sock.sendall(header + payload)
        print("Data sent successfully")

        # Shutdown write half of connection
        sock.shutdown(socket.SHUT_WR)
        print("Connection closed")

        return True

    except socket.timeout:
        print("ERROR: Connection timed out")
        return False
    except ConnectionRefusedError:
        print("ERROR: Connection refused. Is the receiver running?")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False
    finally:
        sock.close()

def main():
    # Parse arguments
    host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 9005

    # Test recipe
    recipe_steps = [
        "Preheat oven to 350°F (175°C)",
        "Mix 2 cups flour, 1 cup sugar, and 1/2 tsp salt in a bowl",
        "Add 3 eggs and 1/2 cup milk, mix until smooth",
        "Pour batter into greased 9x13 pan",
        "Bake for 25-30 minutes until golden brown",
        "Let cool for 10 minutes before serving"
    ]

    print("=" * 60)
    print("Recipe TCP Sender Test")
    print("=" * 60)
    print(f"Target: {host}:{port}")
    print(f"Recipe steps to send:")
    for i, step in enumerate(recipe_steps, 1):
        print(f"  {i}. {step}")
    print("=" * 60)
    print()

    success = send_recipe(host, port, recipe_steps)

    if success:
        print("\n✓ Recipe sent successfully!")
        return 0
    else:
        print("\n✗ Failed to send recipe")
        return 1

if __name__ == "__main__":
    sys.exit(main())
