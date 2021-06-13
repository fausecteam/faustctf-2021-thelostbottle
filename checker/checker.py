#!/usr/bin/env python3

from ctf_gameserver import checkerlib

import utils
import json
import base64
import logging
import socket
import random

import layout
import player
#from player import * # unittest

from util import *

class LostbottleChecker(checkerlib.BaseChecker):

	"""
	pair of sending a message and receiving an answer
	similar to client/server communicate() but randomizes json a bit and is more verbose
	"""
	def communicate(self, socket, msg):
		logging.info(f">> {msg}")
		# only difference to send_json is the random indent
		msg_str = json.dumps(msg, indent=random.choice(['', ' ', '  ', '\t', '    '])).encode()
		msg_encoded = base64.b64encode(msg_str)
		mlen = len(msg_encoded)
		assert mlen <= MAX_MSG_SIZE, "Message too long"
		sz = pack('I', mlen)
		socket.send(sz)
		socket.send(msg_encoded)
		socket.send(sz)
		# send_json end
		m = recv_json(socket)
		logging.info(f"<< {m}")
		if not m["success"]:
			logging.info(f"Result is false: {m['msg']}")
			return None
		return m["msg"]

	def commwrapper(self, data):
		return self.communicate(self.socket, data)

	def connect(self, ip):
		self.socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
		self.socket.connect((ip, 5555, 0, 0))
		logging.info("Connecting ...")
		return self.socket
	
	def disconnect(self, send_disconnect_msg = True):
		if send_disconnect_msg:
			send_json(self.socket, {"type": "GBYE"})
		self.socket.close()
	
	def place_flag(self, tick):
		flag = checkerlib.get_flag(tick)
		logging.info("Placing Flag %s for tick %d" % (flag, tick))
		mapdata = layout.gen_map(flag)
		use_map = base64.b64encode(json.dumps(mapdata["map"]).encode()).decode()

		self.connect(self.ip)
		logging.info("Uploading map with flag")
		val = self.commwrapper({"type": "UPLD", "map": use_map})
		mapdata["file"] = val

		logging.info(f"Uploaded as {val}. Now playing the map")
		play = self.commwrapper({"type": "HELO", "cmd": "new", "map": val})
		logging.info(".. and save the current state")
		save = self.commwrapper({"type": "SAVE"})
		mapdata["save"] = save
		checkerlib.store_state(str(tick), mapdata)
		self.disconnect()
		checkerlib.set_flagid(mapdata["file"])
		logging.info(json.dumps(mapdata, indent='\t'))
		return checkerlib.CheckResult.OK

	def check_service(self):
		self.connect(self.ip)
		val = self.commwrapper({"type": "HELO", "cmd": "new", "map": "maps/smallmap.json"})
		if not val:
			return checkerlib.CheckResult.DOWN
		self.disconnect()
		# Unittest
		player.TARGET = self.ip # Target inside the unittest file
		try:
			t = player.TestServer()
			t.setUp()
			t.test_samplemap()
			t.tearDown()
		except AssertionError as e:
			logging.info(e)
			return checkerlib.CheckResult.FAULTY
		except SystemExit as e:
			logging.info("SystemExit in playertest")
			logging.info(e)
			return checkerlib.CheckResult.FAULTY
		return checkerlib.CheckResult.OK

	def check_flag(self, tick):
		try:
			expect_flag = checkerlib.get_flag(tick)
			logging.info("Checking flag %s for tick %d" % (expect_flag, tick))
			# get data and delete sign values (prepare for load game state)
			data = checkerlib.load_state(str(tick))
			if data == None:
				logging.error("No checker state exists for tick %d" % tick)
				return checkerlib.CheckResult.FLAG_NOT_FOUND

			self.connect(self.ip)
			val = self.commwrapper({"type": "HELO", "cmd": "load", "map": data["save"]})
			if not val:
				logging.error("HELO failed")
				return checkerlib.CheckResult.FLAG_NOT_FOUND
			# Check Sign
			if not self.move(data["signpath"]):
				return checkerlib.CheckResult.FLAG_NOT_FOUND
			val = self.commwrapper({"type": "INAK", "pos": data["signpos"]})
			if not val:
				logging.error("Querying flag content failed")
				return checkerlib.CheckResult.FLAG_NOT_FOUND
			if val != expect_flag:
				logging.error("Expect flag %s, found %s" % (expect_flag, val))
				return checkerlib.CheckResult.FLAG_NOT_FOUND
			logging.info("=== Found Flag in Sign ===")
			# Check Bottles
			val = self.commwrapper({"type": "HELO", "cmd": "load", "map": data["save"]})
			if not self.move(data["bottlepath"]):
				return checkerlib.CheckResult.FLAG_NOT_FOUND
			for b in data["bottleorder"]:
				val = self.commwrapper({"type": "INAK", "pos": b})
				if not val:
					logging.error("INAK not possible")
					return checkerlib.CheckResult.FLAG_NOT_FOUND
			if expect_flag not in val:
				logging.error("Flag %s not found in bottle string %s" % (expect_flag, val))
				return checkerlib.CheckResult.FLAG_NOT_FOUND
			logging.info("=== Found Flag in Bottles ===")
			self.disconnect()
			return checkerlib.CheckResult.OK
		except SystemExit as e:
			logging.error("Failed checking the flag. Probably service died?")
			logging.error(e)
			return checkerlib.CheckResult.FLAG_NOT_FOUND
	
	def move(self, path):
		for p in path:
			val = self.commwrapper({"type": "ROOM", "exit": (p[0], p[1]), "pwd": p[2]})
			try:
				check_has(val, ["room", "pos"])
			except RuntimeError as e:
				logging.error("Entering room gives unexpected result {val} with error {e}")
				return False
		return True

if __name__ == '__main__':

	checkerlib.run_check(LostbottleChecker)
