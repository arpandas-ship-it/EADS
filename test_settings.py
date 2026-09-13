import json
import sys
from urllib import error, request

BASE_URL = "http://127.0.0.1:5000/api"
REQUEST_TIMEOUT = 5


def check_api(name, method, url, data=None):
    try:
        if method not in {"GET", "POST", "PUT"}:
            raise ValueError(f"Unsupported HTTP method: {method}")

        body = None
        headers = {}

        if data is not None:
            body = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"

        response = request.urlopen(
            request.Request(
                url,
                data=body,
                headers=headers,
                method=method
            ),
            timeout=REQUEST_TIMEOUT
        )

        response_body = response.read().decode("utf-8")

        print(f"\n{name}")
        print(f"Status: {response.status}")

        try:
            print(json.loads(response_body))
        except json.JSONDecodeError:
            print(response_body)

        return response.status < 400

    except error.HTTPError as exc:
        print(f"\n{name}")
        print(f"Status: {exc.code}")
        print(exc.read().decode("utf-8"))
        return False

    except (error.URLError, TimeoutError):
        print(f"\n{name}")
        print("ERROR: API server is not running.")
        return False

    except Exception as e:
        print(f"\n{name}")
        print("ERROR:", e)
        return False


def run_tests():

    print("=" * 60)
    print("EADS - COMPLETE SYSTEM TEST")
    print("=" * 60)

    results = []

    # 1. Server test
    results.append(
        check_api(
            "1. Server Health Test",
            "GET",
            f"{BASE_URL}/health"
        )
    )

    # 2. Emergency API
    results.append(
        check_api(
            "2. Emergency API Test",
            "GET",
            f"{BASE_URL}/emergencies"
        )
    )

    # 3. Ambulance API
    results.append(
        check_api(
            "3. Ambulance API Test",
            "GET",
            f"{BASE_URL}/ambulances"
        )
    )

    # 4. Hospital API
    results.append(
        check_api(
            "4. Hospital API Test",
            "GET",
            f"{BASE_URL}/hospitals"
        )
    )

    # 5. User API
    results.append(
        check_api(
            "5. User API Test",
            "GET",
            f"{BASE_URL}/users"
        )
    )

    # 6. Tracking API
    results.append(
        check_api(
            "6. Active Tracking Test",
            "GET",
            f"{BASE_URL}/tracking/active"
        )
    )

    # 7. Reports API
    results.append(
        check_api(
            "7. Reports API Test",
            "GET",
            f"{BASE_URL}/reports/summary"
        )
    )

    # Final result
    passed = sum(results)
    total = len(results)

    print("\n" + "=" * 60)
    print("SYSTEM TEST RESULT")
    print("=" * 60)

    print(f"Tests Passed : {passed}")
    print(f"Tests Failed : {total - passed}")
    print(f"Total Tests  : {total}")

    if passed == total:
        print("\nSYSTEM STATUS: ALL TESTS PASSED")
    else:
        print("\nSYSTEM STATUS: SOME TESTS FAILED")

    print("=" * 60)

    return passed == total


if __name__ == "__main__":
    sys.exit(0 if run_tests() else 1)