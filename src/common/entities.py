"""
All entities in the game
These structures are shared between server and client
"""

from common.util import *
from ffserver.element_types import *

""" When jsonifying the data, actual content slightly depends on JSON_TYPE """
JSON_SERVER_TO_CLIENT = 1
JSON_CLIENT_TO_SERVER = 2
JSON_SAVING = 3

class Element():
	__slots__ = [
		"id",
		"changed",
		"x",
		"y",
		"value",
		"uuid"
		]

	def __init__(self):
		self.changed = False
		self.value = ""
	
	def parse(self, j, merge = False):
		check_has(j, ["x", "y", "id"])
		self.x = j["x"]
		self.y = j["y"]
		if j["id"] not in ELEMENT_TYPES:
			fail("Element type unknown")
		self.id = j["id"]
		if ELEMENT_TYPES[self.id]["hasValue"]:
			if "value" in j:
				self.value = j["value"]
				self.changed = merge # changed is only true, if the map was merged (loading) and contains a value
	
	"""
	store: if True, compute storing relevant stuff, else data is sent to client
	"""
	def to_jsonable(self, json_type):
		j = {
			"x": self.x,
			"y": self.y,
			"id": self.id,
			"value": self.value
		}
		return j
	
	def set_value(self, new_val):
		self.value = new_val
		self.changed = True

class Sign(Element):
	def __init__(self):
		super().__init__()
	
	def get_shortvalue(self):
		msg = self.value
		if len(msg) > 8:
			msg = msg[:4] + "\n..."
		elif len(msg) > 4:
			msg = msg[:4] + "\n" + msg[4:]
		return msg
	
	def to_jsonable(self, json_type):
		j = super().to_jsonable(json_type)
		if json_type == JSON_SAVING:
			if not self.changed:
				del j["value"] # only save sign value if it was changed, otherwise who cares?
			# otherwise sent the full value to save it
		else: # sending to play .. use the short value displayed
			j["value"] = self.get_shortvalue()
		return j

class Bottle(Element):
	def __init__(self):
		super().__init__()
	
	def to_jsonable(self, json_type):
		j = super().to_jsonable(json_type)
		del j["value"] # who cares, bottles cannot be changed
		return j

class Room():
	__slots__ = [
		"name",
		"map",
		"background",
		"w",
		"h",
		"saveable",
		"blocks",
		"exits",
		"elements"
		]

	def __init__(self, name, map):
		self.name = name
		self.map = map
		self.blocks = {}
		self.exits = {}
		self.elements = {}
		self.saveable = True

	"""
	Parse Room from dictionary and built internal data structures
	merge := if True, only loads the relevant information from a saved state into the preexisting world
	"""
	def parse(self, j, merge = False):
		check_has(j, ["w", "h", "blocks", "exits", "elements"])
		self.w = j["w"]
		self.h = j["h"]
		self.background = j["background"]
		if not merge:
			self.saveable = j["saveable"]

		# Blocks (just some movement blockers)
		for b in j["blocks"]:
			check_has(b, ["img", "pos"])
			for x, y in b["pos"]:
				p = (x, y)
				if p in self.blocks and not merge:
					fail(f"Position {p} occupied by two blocks")
				self.blocks[p] = {"img": b["img"], "pos": [[x, y]]}

		# Exits (exits to other rooms)
		for e in j["exits"]:
			check_has(e, ["x", "y"])
			p = (e["x"], e["y"])
			if p in self.exits and not merge:
				fail("Two exits at the same location")
			if self.map != None and e["room"] not in self.map.rooms: # only check on server
				fail("Exit leads to nowhere")
			if "room" in e and e["room"] == self.name:
				fail("Exit leads to room itself")
			if not merge:
				if "keypad" not in e:
					fail("Missing keypad entry")
				keypad = e["keypad"]
			else:
				keypad = None
			self.exits[p] = {"open": e["open"], "keypad": keypad}
			if "room" in e:
				self.exits[p]["room"] = e["room"]
				self.exits[p]["targetx"] = e["targetx"]
				self.exits[p]["targety"] = e["targety"]

		for uuid, el in j["elements"].items():
			check_has(el, ["x", "y", "id"])
			p = (el["x"], el["y"])
			if merge:
				if p in self.elements:
					if self.elements[p].uuid != uuid:
						fail("UUID mismatch of elements")
				else:
					fail("No element here in the base map")
			else: # base map
				if p in self.elements:
					fail("Two elements at the same location")
				else:
					if el["id"] == ELEMENT_SIGN:
						self.elements[p] = Sign()
					elif el["id"] == ELEMENT_BOTTLE:
						self.elements[p] = Bottle()
					else:
						self.elements[p] = Element()
					self.elements[p].uuid = uuid
			self.elements[p].parse(el, merge)

	"""
	Convert the class to an ordinary dictionary
	"""
	def to_jsonable(self, json_type):
		v = {
			"w": self.w,
			"h": self.h,
			"background": self.background,
			"saveable": self.saveable,
			"exits": [],
			"blocks": [
				{
					"img": self.blocks[bl]["img"],
					"pos": self.blocks[bl]["pos"]
				}
				for bl in self.blocks]
		}
		for ex in self.exits:
			e = {
				"x": ex[0],
				"y": ex[1],
				"open": self.exits[ex]["open"],
				"keypad": ((json_type == JSON_SERVER_TO_CLIENT) and (self.exits[ex]["keypad"] != None))
			}
			if json_type == JSON_SAVING:
				e["targetx"] = self.exits[ex]["targetx"]
				e["targety"] = self.exits[ex]["targety"]
				e["room"] = self.exits[ex]["room"]
			v["exits"] += [e]
		if json_type == JSON_SERVER_TO_CLIENT:
			v["elements"] = {}
			i = 0 # using short ids saves transfer time
			for k, el in self.elements.items():
				v["elements"]["e{}".format(i)] = el.to_jsonable(json_type)
				i += 1
		else: # saving
			v["elements"] = {
				el.uuid : el.to_jsonable(json_type)
				for k, el in self.elements.items()}
		return v

class Map():
	__slots__ = [
		"name",
		"rooms",
		"globals",
		"dreams"
	]

	def __init__(self):
		pass

	"""
	merge := if True, only loads the relevant information from a saved state into the preexisting world
	"""
	def parse(self, j, name, merge = False):
		check_has(j, ["rooms", "globals"])
		check_has(j["globals"], ["posx", "posy", "room"])

		if not merge:
			self.name = name
			self.rooms = {}
			self.dreams = j["dreams"]
		# initialize first, then parse because we need to 'define' rooms before parsing the exits
		for r in j["rooms"]:
			if not r in self.rooms:
				self.rooms[r] = Room(r, self)
		for r in j["rooms"]:
			self.rooms[r].parse(j["rooms"][r], merge)

		if j["globals"]["room"] not in self.rooms:
			fail("Starting room does not exist")
		if not self.rooms[j["globals"]["room"]].saveable:
			fail("State corrupted. Cannot start in a room with disabled saving")
		self.globals = j["globals"]

"""
Current state of the player
"""
class State():
	__slots__ = [
		"map",
		"room_name",
		"room",
		"last_enter",
		"drunkness"
	]

	def __init__(self, j, name):
		check_has(j, ["globals"])
		self.map = Map()
		self.map.parse(j, name)
		self.room_name = j["globals"]["room"]
		self.room = self.map.rooms[self.room_name]
		self.last_enter = (j["globals"]["posx"], j["globals"]["posy"])
		self.drunkness = {
			"volume": 4, # liters of blood
			"percent": 0, # ratio of alcohol
		}
	
	"""
	merge := if True, only loads the relevant information from a saved state into the preexisting world
	"""
	def parse(self, j, name, merge = False):
		self.map.parse(j, name, merge)
		self.room_name = j["globals"]["room"]
		self.room = self.map.rooms[self.room_name]
		self.last_enter = (j["globals"]["posx"], j["globals"]["posy"])

