import unittest

from cobe.cache import LRUCache

class testLRUCache(unittest.TestCase):
    def testSetGet(self):
        cache = LRUCache()

        self.assertEquals(0, len(cache))
        cache["testKey"] = "testValue"

        self.assertEquals(1, len(cache))
        self.assertEquals("testValue", cache["testKey"])

    def testEvict(self):
        cache = LRUCache(num_items=2)

        self.assertEquals(0, len(cache))
        cache["testKey1"] = "testValue1"
        cache["testKey2"] = "testValue2"

        self.assertEquals(2, len(cache))
        self.assertEquals("testValue1", cache["testKey1"])
        self.assertEquals("testValue2", cache["testKey2"])

        cache["testKey3"] = "testValue3"
        self.assertEquals(2, len(cache))
        self.assertEquals("testValue2", cache["testKey2"])
        self.assertEquals("testValue3", cache["testKey3"])

        # access testKey2 so it has been used more recently than testKey3
        cache["testKey2"]
        cache["testKey1"] = "testValue1"
        self.assertEquals(2, len(cache))
        self.assertEquals("testValue1", cache["testKey1"])
        self.assertEquals("testValue2", cache["testKey2"])

if __name__ == '__main__':
    unittest.main()
