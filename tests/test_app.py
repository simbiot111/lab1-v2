# tests/test_app.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'flaskapp')))

import unittest
from some_app import adjust_contrast
from PIL import Image
import numpy as np

class TestContrast(unittest.TestCase):
    def test_contrast_identity(self):
        img = Image.new('RGB', (10, 10), color='gray')
        result = adjust_contrast(img, 1.0)
        self.assertEqual(result.tobytes(), img.tobytes())
    
    def test_contrast_zero(self):
        img = Image.new('RGB', (10, 10), color=(100, 100, 100))
        result = adjust_contrast(img, 0.0)
        arr = np.array(result)
        self.assertTrue(np.all(arr == 128))

if __name__ == '__main__':
    unittest.main()