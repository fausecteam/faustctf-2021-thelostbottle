import threading
import json
import unittest
import socket

from util import *
from ffserver.server import Game
from common.entities import *

class TestServer(unittest.TestCase):
	def setUp(self):
		self.game = Game(False, None)

	def tearDown(self):
		pass

	def test_loading(self):
		self.game.load_map("maps/smallmap.json")
		# secret room
		sr = self.game.state.map.rooms["secret_room"]
		self.assertEqual(len(sr.elements), 1)
		sign = sr.elements[(5, 5)]
		self.assertEqual(sign.uuid, "gsdsgskh")
		self.assertIsInstance(sign, Sign)
		self.assertFalse(sign.changed)
		js = sign.to_jsonable(JSON_SAVING)
		self.assertNotIn("value", js)
	
if __name__ == "__main__":
	unittest.main()
