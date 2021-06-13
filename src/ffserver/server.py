import json
import sys
import base64
import re
import os
import subprocess
import traceback
import socket
import random
import string

from ffserver.element_types import *
from ffserver.util import *
from common.entities import *
from common.util import *

class ClientException(Exception):
	pass

def rndstring():
	return "".join(random.choice(string.ascii_lowercase) for _ in range(7))

class Game():
	__slots__ = [
		"state",
		"context",
		"socket"
	]

	"""
	Init the network. Just some magic for different start options
	argv := HOST and PORT. If not used, assume systemd activation
	use_network := boolean, if False, server can be embedded into other applications
	"""
	def __init__(self, use_network, argv):
		self.state = None
		if not use_network:
			return
		ci = None
		if len(argv) > 1:
			ip = argv[1]
			if len(argv) > 2:
				port = int(argv[2])
			else:
				port = 5555
			ci = (ip, port)
		self.setup_network(ci)

	"""
	Create the network. Magic to get a socket
	connect_info := (HOST, PORT) tuple, if None, assume systemd activation and we take the systemd socket
	"""
	def setup_network(self, connect_info = None):
		if connect_info:
			sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
			sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			sock.bind((connect_info))
			sock.listen(10)
			self.socket = sock.accept()[0]
		else:
			# systemd socket activated, we take the existing socket
			self.socket = socket.fromfd(3, socket.AF_INET6, socket.SOCK_STREAM)
		self.socket.settimeout(60) # drop connection after idleling for too long

	def close_network(self):
		self.socket.close()

	def load_map(self, filename):
		if re.fullmatch(r"maps/[a-zA-Z0-9_]+.json", filename) == None:
			self.fail_client("Not a valid map name")
		if not os.path.isfile(filename):
			self.fail_client("Map does not exist")

		with open(filename) as inf:
			m = json.load(inf)
		self.state = State(m, filename)

	def run(self):
		"""
		Main Loop: get a message from client and process it
		Always need to send a response to be able to receive again
		"""
		while True:
			try:
				msg = recv_json(self.socket)
				if "type" not in msg:
					self.fail_client("Missing type in message")
				elif msg["type"] == "UPLD":
					self.handle_upld(msg)
				elif msg["type"] == "HELO":
					self.handle_helo(msg)
				elif msg["type"] == "ROOM":
					self.handle_room(msg)
				elif msg["type"] == "INAK":
					self.handle_interact(msg)
				elif msg["type"] == "SIGN":
					self.handle_sign(msg)
				elif msg["type"] == "SAVE":
					self.handle_save(msg)
				elif msg["type"] == "GBYE":
					break
				else:
					self.fail_client("Invalid msg type")
			except ClientException as e:
				print("The client sent garbage")
				print(traceback.format_exc())
				self.close_network()
				sys.exit(1)
			except Exception as e:
				send_json(self.socket, {"success": False, "msg": e.args})
				print(traceback.format_exc())
				sys.exit(1)
			except RuntimeError as e:
				print("Something went wrong")
				self.fail_client(e.args)
				print(traceback.format_exc())
				self.close_network()
				sys.exit(1)
		self.close_network()

	def fail_client(self, msg):
		send_json(self.socket, {"success": False, "msg": msg})
		raise ClientException(msg)

	def respond(self, msg):
		send_json(self.socket, {"success": True, "msg": msg})

	"""
	================================================================================
		      handlers for all client messages
	================================================================================
	"""
	def handle_upld(self, msg):
		check_has(msg, ["map"])
		map_data = base64.b64decode(msg["map"].encode()).decode()
		tries = 0
		while tries < 100:
			try:
				fn = f"maps/map_{rndstring()}.json"
				with open(fn, "x") as outf:
					outf.write(map_data)
				break
			except FileExistsError as e:
				tries += 1
		if tries == 100:
			self.fail_client("No usable file name. Giving up")
		self.respond(fn)

	""" First connect -> send the current/initial room """
	def handle_helo(self, msg):
		check_has(msg, ["cmd", "map"])
		if msg["cmd"] == "new":
			self.load_map(msg["map"])
		elif msg["cmd"] == "load":
			if len(msg["map"]) < 4:
				self.fail_client("Invalid map")
			decoded = base64.b64decode(msg["map"])
			if decoded[:4] == b"affm": # binformat
				cmd = [
					"./binformat",
					"m2j",
					"-",
					"-"]
				storageProc = subprocess.Popen(cmd,
					stdin=subprocess.PIPE,
					stdout=subprocess.PIPE,
					stderr=subprocess.PIPE
					)
				stdout, stderr = storageProc.communicate(decoded)
				if len(stderr) > 0:
					print(stderr)
					self.fail_client(f"Internal fail {stderr}")
					return
				save_state = json.loads(stdout)
			else: # json format
				save_state = json.loads(decoded.decode())
			check_has(save_state, ["map"])
			orig_map = save_state["map"]
			self.load_map(orig_map)
			self.state.parse(save_state, None, merge = True)
		else:
			self.fail_client("Invalid command")
		self.respond({"room": self.state.room.to_jsonable(JSON_SERVER_TO_CLIENT), "pos": (self.state.map.globals["posx"], self.state.map.globals["posy"])})

	def handle_room(self, msg):
		check_has(msg, ["exit", "pwd"])
		pos = tuple(msg["exit"])
		if not pos in self.state.room.exits:
			self.fail_client("No exit at this location")
		exit = self.state.room.exits[pos]
		if not exit["open"]:
			self.fail_client("Exit is closed")
		if exit["keypad"] != None and exit["keypad"] != msg["pwd"]:
			self.fail_client("Wrong phrase")
		new_room_name = exit["room"]
		new_room = self.state.map.rooms[new_room_name]
		epos = (exit["targetx"], exit["targety"])
		self.state.room_name = new_room_name
		self.state.room = new_room
		self.state.last_enter = epos
		self.respond({"room": new_room.to_jsonable(JSON_SERVER_TO_CLIENT), "pos": epos})

	def handle_sign(self, msg):
		check_has(msg, ["pos", "value"])
		pos = tuple(msg["pos"])
		if not pos in self.state.room.elements:
			self.fail_client("No sign at this location")
		el = self.state.room.elements[pos]
		if el.id != ELEMENT_SIGN:
			self.fail_client("Not a sign at this location")
		el.set_value(msg["value"])
		self.respond("ACK")

	def handle_interact(self, msg):
		check_has(msg, ["pos"])
		pos = tuple(msg["pos"])
		if not pos in self.state.room.elements:
			self.fail_client(f"No element at this location {pos}")
		el = self.state.room.elements[pos]
		handlers = [
			None,
			self.handle_el_sign,
			self.handle_el_control,
			self.handle_el_key,
			self.handle_el_barrel,
			self.handle_el_bottle
		]
		handlers[el.id](msg, el)

	def handle_el_sign(self, msg, el):
		self.respond(el.value)

	def handle_el_control(self, msg, el):
		s = el.value.split(":")
		cmd = s[0]
		args = s[1:]
		if cmd == "opendoor":
			pos = (int(args[0]), int(args[1]))
			if not pos in self.state.room.exits:
				self.fail_client("Door nonexistant")
			self.state.room.exits[pos]["open"] = True
		else:
			self.fail_client("Invalid control command")
		self.respond(el.value)

	""" Keys are meaningless """
	def handle_el_key(self, msg, el):
		self.respond("ACK")
	
	def handle_el_barrel(self, msg, el):
		if el.value == "intact":
			el.value = "broken"
		self.respond(el.value)
	
	def handle_el_bottle(self, msg, el):
		if el.value == "empty":
			self.respond("This bottle is already empty.")
			return
		a = el.value.split("|")
		volume = int(a[0])
		percent = int(a[1].replace("%", ""))
		el.value = "empty"
		self.drink(volume, percent)
		for i in range(len(self.state.map.dreams)-1, -1, -1):
			if self.state.drunkness["percent"] >= self.state.map.dreams[i][0]:
				self.respond(self.state.map.dreams[i][1])
				return
		self.respond("You feel sober. Time to find your rum.")
	
	""" Saving the game -> a save state with all relevant information """
	def handle_save(self, msg):
		if not self.state.room.saveable:
			self.fail_client("Saving is disabled in this room")
		save = json.dumps({
			# the rooms
			"rooms": {
				r: self.state.map.rooms[r].to_jsonable(JSON_SAVING)
				for r in self.state.map.rooms
			},
			# current position
			"globals": {
				"posx": self.state.last_enter[0],
				"posy": self.state.last_enter[1],
				"room": self.state.room_name
			},
			# the base map to use
			"map": self.state.map.name
		})
		cmd = [
			"./binformat",
			"j2m",
			"-",
			"-"]
		storageProc = subprocess.Popen(cmd,
			stdin=subprocess.PIPE,
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE
			)
		stdout, stderr = storageProc.communicate(save.encode())
		if len(stderr) > 0:
			print(stderr)
			self.fail_client(f"Internal fail generating the save file {stderr}")
			return
		b64code = base64.b64encode(stdout)
		self.respond(b64code.decode())
	
	def drink(self, volume, percent):
		"""
		Highly accurate blood alcohol simulation for pirates:
		When drinking 'volume' liters of liquids, the same amount of blood is
		drained from circulation to free space for the new liquids that are
		directly transferred to the pirate's blood circulation system. There,
		the liquids mix with all preexisting blood an liquids.
		Trust me, I am a piratologist.
		"""
		y = self.state.drunkness["percent"]
		self.state.drunkness["percent"] = (y * (4 - volume) + percent * volume) / 4
