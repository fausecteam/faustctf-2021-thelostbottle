import threading
import json
import unittest
import socket

from util import *

TARGET = "::1"

class TestServer(unittest.TestCase):
	def setUp(self):
		self.socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
		print("Setting up with target ", TARGET)
		self.socket.connect((TARGET, 5555, 0, 0))

	def tearDown(self):
		send_json(self.socket, {"type": "GBYE"})
		self.socket.close()

	def test_samplemap(self):
		# Connect
		v = communicate(self.socket, {"type": "HELO", "cmd": "new", "map": "maps/smallmap.json"})
		check_has(v, ["pos", "room"])
		self.assertEqual(v["pos"], [1, 1], "Starting location invalid")
		# Activate control
		v = communicate(self.socket, {"type": "INAK", "pos": [6, 5]})
		self.assertEqual(v, "opendoor:19:6", "Lever command invalid")
		v = communicate(self.socket, {"type": "INAK", "pos": [8, 1]}) # barrel
		self.assertEqual(v, "broken", "Barrel not destroyed")
		# Change room
		v = communicate(self.socket, {"type": "ROOM", "exit": [19, 6], "pwd": None})
		check_has(v, ["pos", "room"])
		# Read sign
		v = communicate(self.socket, {"type": "INAK", "pos": [7, 7]})
		self.assertEqual(v, "The rum is a lie", "Sign value invalid")
		# Change Sign
		v = communicate(self.socket, {"type": "SIGN", "pos": [7, 7], "value": "New Text"})
		self.assertEqual(v, "ACK", "Changing sign content misses ACK")
		v = communicate(self.socket, {"type": "INAK", "pos": [7, 7]})
		self.assertEqual(v, "New Text", "New sign text not saved")
		# download
		save = communicate(self.socket, {"type": "SAVE"})
		b64decode = base64.b64decode(save) # just check that this does not fail
		self.assertEqual(b64decode[:4], b'affm', "Binary not starting with affm")
		# Change to secret room
		v = communicate(self.socket, {"type": "ROOM", "exit": [9, 5], "pwd": "magic"})
		check_has(v, ["pos", "room"])
		# upload saved map an check modifies are in place
		v = communicate(self.socket, {"type": "HELO", "cmd": "load", "map": save})
		check_has(v, ["pos", "room"])
		self.assertEqual(v["pos"], [1, 3], "Starting position after load mismatch") # position
		self.assertEqual(v["room"]["w"], 10, "After loading room width invalid (maybe wrong room)?") # room
		v = communicate(self.socket, {"type": "INAK", "pos": [7, 7]}) # sign
		self.assertEqual(v, "New Text", "Sign text after loading not correct")
		# change room back for barrel
		v = communicate(self.socket, {"type": "ROOM", "exit": [0, 3], "pwd": None})
		check_has(v, ["pos", "room"])
		for e in v["room"]["elements"]: # barrel
			el = v["room"]["elements"][e]
			if el["x"] == 8 and el["y"] == 1:
				self.assertEqual(el["value"], "broken", "After loading, barrel is not broken")
				break
		else:
			self.assertTrue(False, "Destroyed barrel not found")
		
	
	def test_binarysaveloading(self):
		# Connect
		v = communicate(self.socket, {"type": "HELO", "cmd": "new", "map": "maps/smallmap.json"})
		check_has(v, ["pos", "room"])
		self.assertEqual(v["pos"], [1, 1], "binarytext initial position wrong")
		save = communicate(self.socket, {"type": "SAVE"})
		b64decode = base64.b64decode(save) # just check that this does not fail
		self.assertEqual(b64decode[:4], b'affm', "binary not starting with 'affm'")
		v = communicate(self.socket, {"type": "HELO", "cmd": "load", "map": save})
		check_has(v, ["pos", "room"])
		self.assertEqual(v["pos"], [1, 1], "after binary loading, position is invalid")
	
	def test_INAK_nonexistent(self):
		# Connect
		v = communicate(self.socket, {"type": "HELO", "cmd": "new", "map": "maps/smallmap.json"})
		check_has(v, ["pos", "room"])
		self.assertEqual(v["pos"], [1, 1])
		# Activate control
		with self.assertRaises(SystemExit) as cm:
			print("Expecting to fail here")
			v = communicate(self.socket, {"type": "INAK", "pos": [6, 4]})

if __name__ == "__main__":
	unittest.main()
