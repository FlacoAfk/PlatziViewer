import json
import sys
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

URL = 'http://localhost:8080/api/self-check-drive'


def main():
    try:
        with urlopen(URL, timeout=10) as response:
            payload = response.read().decode('utf-8')
            report = json.loads(payload)
    except HTTPError as exc:
        print(f'❌ HTTP error: {exc.code} {exc.reason}')
        sys.exit(1)
    except URLError as exc:
        print(f'❌ Connection error: {exc.reason}')
        print('   Asegúrate de tener el servidor corriendo: python server.py')
        sys.exit(1)
    except Exception as exc:
        print(f'❌ Unexpected error: {exc}')
        sys.exit(1)

    print('=== Drive Self-Check ===')
    print(f"ok: {report.get('ok')}")
    print(f"message: {report.get('message')}")
    print(f"generatedAt: {report.get('generatedAt')}")
    print(f"totalRefs: {report.get('totalRefs')}")
    print(f"validDriveRefs: {report.get('validDriveRefs')}")
    print(f"localRefs: {report.get('localRefs')}")
    print(f"invalidRefs: {report.get('invalidRefs')}")
    print(f"emptyRefs: {report.get('emptyRefs')}")

    issues = report.get('issues') or []
    if issues:
        print('\n--- First issues ---')
        for issue in issues[:15]:
            print(f"- {issue.get('reason')}: {issue.get('location')} => {issue.get('value')}")

    sys.exit(0 if report.get('ok') else 2)


if __name__ == '__main__':
    main()
