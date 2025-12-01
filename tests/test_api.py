import urllib.request
import json
import unittest

BASE_URL = "http://127.0.0.1:8000"

class TestCDAPI(unittest.TestCase):
    def test_1_create_cd(self):
        url = f"{BASE_URL}/cds/"
        data = {
            "title": "Test CD",
            "artist": "Test Artist",
            "year": 2023
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req) as response:
            self.assertEqual(response.status, 200)
            result = json.loads(response.read().decode())
            self.assertEqual(result['title'], "Test CD")
            self.assertEqual(result['artist'], "Test Artist")
            self.assertIsNotNone(result.get('id'))

    def test_2_list_cds(self):
        url = f"{BASE_URL}/cds/"
        with urllib.request.urlopen(url) as response:
            self.assertEqual(response.status, 200)
            result = json.loads(response.read().decode())
            self.assertIsInstance(result, list)
            # Check if our created CD is in the list
            found = any(cd['title'] == "Test CD" for cd in result)
            self.assertTrue(found)

    def test_3_get_cd(self):
        # First create a CD to ensure we have an ID
        url = f"{BASE_URL}/cds/"
        data = {"title": "Get Test", "artist": "Get Artist", "year": 2024}
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req) as response:
            cd_data = json.loads(response.read().decode())
            cd_id = cd_data['id']

        # Now get it
        url = f"{BASE_URL}/cds/{cd_id}"
        with urllib.request.urlopen(url) as response:
            self.assertEqual(response.status, 200)
            result = json.loads(response.read().decode())
            self.assertEqual(result['id'], cd_id)
            self.assertEqual(result['title'], "Get Test")

if __name__ == '__main__':
    unittest.main()
