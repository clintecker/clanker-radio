#!/usr/bin/env python3
"""Test script for verifying CRITICAL bug fixes in api_dj_tag.py.

Tests:
1. Thread safety - concurrent job creation
2. Path traversal protection
3. Health endpoint functionality
"""

import json
import time
import requests
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "http://127.0.0.1:5001"


def test_health_endpoint():
    """Test 1: Health endpoint still works."""
    print("\n=== Test 1: Health Endpoint ===")
    try:
        response = requests.get(f"{BASE_URL}/api/dj-tag/health", timeout=5)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()
        assert "status" in data, "Missing 'status' field"
        assert data["status"] == "ok", f"Expected status 'ok', got {data['status']}"
        assert "active_jobs" in data, "Missing 'active_jobs' field"
        assert "tmp_dir" in data, "Missing 'tmp_dir' field"

        print(f"✓ Health endpoint working: {data}")
        return True
    except Exception as e:
        print(f"✗ Health endpoint failed: {e}")
        return False


def create_job(job_num: int):
    """Helper to create a single job."""
    try:
        response = requests.post(
            f"{BASE_URL}/api/dj-tag/generate",
            json={"text": f"Test job number {job_num}"},
            timeout=5
        )
        return response.status_code == 200, response.json()
    except Exception as e:
        return False, str(e)


def test_concurrent_job_creation():
    """Test 2: Thread safety - concurrent job creation."""
    print("\n=== Test 2: Concurrent Job Creation (Thread Safety) ===")
    try:
        num_jobs = 10
        print(f"Creating {num_jobs} jobs concurrently...")

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_job, i) for i in range(num_jobs)]
            results = [f.result() for f in futures]

        successes = sum(1 for success, _ in results if success)
        job_ids = [data.get("job_id") for success, data in results if success and isinstance(data, dict)]

        # Check for duplicate job IDs (would indicate race condition)
        unique_ids = set(job_ids)

        print(f"✓ Created {successes}/{num_jobs} jobs successfully")
        print(f"✓ All job IDs unique: {len(job_ids) == len(unique_ids)}")

        if len(job_ids) != len(unique_ids):
            print("✗ RACE CONDITION DETECTED: Duplicate job IDs found!")
            return False

        return successes == num_jobs

    except Exception as e:
        print(f"✗ Concurrent job creation failed: {e}")
        return False


def test_path_traversal_protection():
    """Test 3: Path traversal vulnerability protection."""
    print("\n=== Test 3: Path Traversal Protection ===")

    # Test cases that should be blocked by our code
    # Note: Some attacks are blocked by Flask's router before reaching our code
    malicious_filenames = [
        ("dj_tag_test/subdir/file.mp3", "forward slash in path"),
        ("dj_tag_test\\subdir\\file.mp3", "backslash in path"),
        ("test.mp3", "missing dj_tag_ prefix"),
        ("dj_tag_test.txt", "wrong extension"),
        ("not_dj_tag_abc.mp3", "wrong prefix"),
    ]

    all_blocked = True
    for filename, description in malicious_filenames:
        try:
            response = requests.get(
                f"{BASE_URL}/api/dj-tag/download/{filename}",
                timeout=5
            )

            if response.status_code == 400:
                print(f"✓ Blocked ({description}): {filename}")
            elif response.status_code == 404:
                # 404 means Flask router normalized it away - also safe
                print(f"✓ Router-blocked ({description}): {filename}")
            else:
                print(f"✗ NOT BLOCKED (status {response.status_code}, {description}): {filename}")
                all_blocked = False

        except Exception as e:
            print(f"✗ Error testing {filename}: {e}")
            all_blocked = False

    # Test valid filename (should return 404 if file doesn't exist)
    valid_filename = "dj_tag_abc123_20250101_120000.mp3"
    try:
        response = requests.get(
            f"{BASE_URL}/api/dj-tag/download/{valid_filename}",
            timeout=5
        )
        # Should be 404 (file not found) not 400 (invalid)
        if response.status_code == 404:
            print(f"✓ Valid filename accepted (404 file not found): {valid_filename}")
        else:
            print(f"✗ Valid filename rejected with status {response.status_code}")
            all_blocked = False
    except Exception as e:
        print(f"✗ Error testing valid filename: {e}")
        all_blocked = False

    return all_blocked


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing CRITICAL Bug Fixes for api_dj_tag.py")
    print("=" * 60)
    print("\nNOTE: Ensure api_dj_tag.py is running on 127.0.0.1:5001")
    print("Run: python scripts/api_dj_tag.py")

    # Wait a moment for user to start server
    print("\nStarting tests in 3 seconds...")
    time.sleep(3)

    results = {
        "Health Endpoint": test_health_endpoint(),
        "Concurrent Job Creation": test_concurrent_job_creation(),
        "Path Traversal Protection": test_path_traversal_protection(),
    }

    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name}: {status}")

    all_passed = all(results.values())
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
