import unittest

from tidal_dl import apiKey


class ApiKeyTests(unittest.TestCase):
    def test_default_api_key_is_valid_tidekeeper_oauth(self):
        index = apiKey.getDefaultIndex()
        item = apiKey.getItem(index)

        self.assertTrue(apiKey.isItemValid(index))
        self.assertEqual(item["platform"], "Tidekeeper OAuth")


if __name__ == "__main__":
    unittest.main()
