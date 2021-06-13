import arcade
import os
import sys
import json
import time
import base64
import socket

from functools import partial

from client.prompt import Prompt
from client.game_config import *
from client.visual_entities import VisRoom
from common.util import *


import tkinter as tk
from tkinter import simpledialog

context = None

class MyGame(arcade.View):
	__slots__ = [
		"rooms",
		"player_sprite",
		"player_list",
		"physics_engine",
		"messages",
		"actions",
		"socket",
		"loaded"
	]

	def __init__(self):
		super().__init__()
		self.loaded = False

		file_path = os.path.dirname(os.path.abspath(__file__))
		os.chdir(file_path)

		# Sprite lists
		self.current_room = None

		# Set up the player
		self.rooms = None
		self.player_sprite = None
		self.player_list = None
		self.physics_engine = None
		self.messages = []
		
		self.actions = {
			"opendoor": self.open_door
		}
		
	def setup(self, socket):
		self.socket = socket

		self.player_sprite = arcade.Sprite("assets/character.png", SCALE * 4 * 1.1)
		self.player_list = arcade.SpriteList()
		self.player_list.append(self.player_sprite)

	def enter_room(self, roomjson, pos):
		self.current_room = VisRoom(roomjson)
		# Create a physics engine for this room
		self.physics_engine = arcade.PhysicsEngineSimple(self.player_sprite, self.current_room.block_list)
		# Position
		self.player_sprite.center_x = (0.5+pos[0]) * BLOCK_SCALED
		self.player_sprite.center_y = (0.5+pos[1]) * BLOCK_SCALED
		self.loaded = True

	def on_draw(self):
		# This command has to happen before we start drawing
		arcade.start_render()
		
		# Not initialized yet
		if not self.loaded:
			arcade.draw_text(
					"Waiting for room info",
					50,
					50,
					arcade.color.RED,
					FONT_SIZE,
					font_name=FONT
					)
			return

		# Draw the background texture
		scale = SCREEN_WIDTH / self.current_room.backImg.width

		arcade.set_background_color(arcade.color.COBALT)
		arcade.draw_lrwh_rectangle_textured(0, 0,
											SCREEN_WIDTH, self.current_room.h * BLOCK_SCALED,
											self.current_room.backImg)

		# Draw the room and all of its contents
		self.current_room.draw()

		self.player_list.draw()
		
		# draw messages
		t = time.time()
		cur = 0
		printed = 0
		linecount = 0
		active = []
		while cur < len(self.messages):
			if self.messages[cur][0] > t:
				txt = self.messages[cur][1]
				txts = [txt[i:i+50] for i in range(0, len(txt), 50)][::-1]
				for text in txts:
					arcade.draw_text(
						text,
						0,
						self.current_room.h * BLOCK_SCALED + linecount * (FONT_SIZE*1.3),
						arcade.color.WHITE,
						FONT_SIZE,
						font_name=FONT
						)
					txt = txt[50:]
					linecount += 1
				printed += 1
				active += [self.messages[cur]]
			cur += 1
		# drop too old messages
		self.messages = active

	def on_key_press(self, key, modifiers):
		if key == arcade.key.UP:
			self.player_sprite.change_y = MOVEMENT_SPEED
		elif key == arcade.key.DOWN:
			self.player_sprite.change_y = -MOVEMENT_SPEED
		elif key == arcade.key.LEFT:
			self.player_sprite.change_x = -MOVEMENT_SPEED
		elif key == arcade.key.RIGHT:
			self.player_sprite.change_x = MOVEMENT_SPEED
		elif key == arcade.key.S:
			if self.current_room.saveable:
				# get a save state
				m = communicate(self.socket, {"type": "SAVE"})
				path = "savefile_{}.bin".format(time.time())
				with open(path, "wb") as outf:
					outf.write(base64.b64decode(m))
				self.add_msg("Saved to {}".format(path))
			else:
				self.add_msg("Saving is disabled for this room")
		elif key == arcade.key.Q:
			# this will not receive an answer
			send_json(self.socket, {"type": "GBYE"})
			sys.exit(0)

	def on_key_release(self, key, modifiers):
		if key == arcade.key.UP or key == arcade.key.DOWN:
			self.player_sprite.change_y = 0
		elif key == arcade.key.LEFT or key == arcade.key.RIGHT:
			self.player_sprite.change_x = 0
		elif key == arcade.key.E:
			# Interact with closest element
			x_pos = int(self.player_sprite.center_x // BLOCK_SCALED)
			y_pos = int(self.player_sprite.center_y // BLOCK_SCALED)
			best = (BLOCK_SCALED**2 * 10, None)
			for x in range(x_pos - 1, x_pos + 2):
				for y in range(y_pos - 1, y_pos + 2):
					dist = ((self.player_sprite.center_x - (x+0.5)*BLOCK_SCALED)**2 +
							(self.player_sprite.center_y - (y+0.5)*BLOCK_SCALED)**2)
					if dist < best[0]:
						if (x, y) in self.current_room.elements:
							best = (dist, self.current_room.elements[(x, y)])
						elif (x, y) in self.current_room.exits:
							if self.current_room.exits[(x, y)]["open"]:
								best = (dist, (x,y))
							else:
								self.add_msg("Ship not ready for travel")
			if best[1] == None:
				print("No element to interact with")
			else:
				el = best[1]
				if isinstance(el, tuple):
					if self.current_room.exits[el]["keypad"]:
						inp = Prompt(self,
								callback = partial(self.use_exit, el),
								initial = "",
								msg = "The captain asks for a secret phrase")
						self.window.show_view(inp)
					else:
						self.use_exit(el, None)
				else:
					val = communicate(self.socket, {"type": "INAK", "pos": (el.x, el.y)})
					if el.id == 1: # Sign
						inp = Prompt(self,
								callback = partial(self.set_el_value, el),
								initial = val,
								msg = "Sign:")
						self.window.show_view(inp)
					elif el.id == 2: # control panel
						s = val.split(":")
						cmd = s[0]
						args = s[1:]
						self.actions[cmd](args)
					elif el.id == 4: # barrel
						el.value = val
						el.update_state()
					elif el.id == 5: # bottle
						self.add_msg(val, timeout=7)
						el.value = "empty"
						el.update_state()

	def set_el_value(self, el, value):
		msg = value
		if len(msg) > 8:
			msg = msg[:4] + "\n..."
		elif len(msg) > 4:
			msg = msg[:4] + "\n" + msg[4:]
		el.set_value(msg)
		communicate(self.socket, {"type": "SIGN", "pos": (el.x, el.y), "value": value})

	def on_update(self, delta_time):
		self.physics_engine.update()

	def use_exit(self, pos, pwd):
		# switch
		val = communicate(self.socket, {"type": "ROOM", "exit": pos, "pwd": pwd})
		if val == "Wrong phrase":
			self.add_msg("Wrong phrase")
			return
		self.enter_room(val["room"], val["pos"])

	def open_door(self, args):
		x = int(args[0])
		y = int(args[1])
		if self.current_room.exits[(x, y)]["open"]:
			return # already open
		self.current_room.exits[(x, y)]["open"] = True
		spr = self.current_room.exits[(x, y)]["sprite"]
		self.current_room.free_list.remove(spr)
		door = arcade.Sprite("assets/ship.png", SCALE * 128 / 80)
		door.center_x = x * BLOCK_SCALED + 0.5 * BLOCK_SCALED
		door.center_y = y * BLOCK_SCALED + 0.5 * BLOCK_SCALED
		door.scale *= 1.2
		self.current_room.exits[(x, y)]["sprite"] = door
		self.current_room.free_list.append(door)

	def add_msg(self, msg, timeout=3):
		self.messages.append((time.time()+timeout, msg))

def usage():
	print("USAGE:")
	print("thelostbottle.py new <MapName> [ip]")
	print("\t\tPass the name of a map known to the server to start playing")
	print("thelostbottle.py load <SaveStateFile> [ip]")
	print("\t\tPass the name of a local saved state to resume playing there")
	sys.exit(1)

def main():
	""" New game or loading save state """
	if len(sys.argv) < 3 or len(sys.argv) > 5:
		usage()

	play_cmd = sys.argv[1]
	play_map = sys.argv[2]
	ip = "::1"
	port = 5555
	if len(sys.argv) >= 4:
		ip = sys.argv[3]
		if len(sys.argv) >= 5:
			port = int(sys.argv[4])

	if play_cmd not in ["new", "load"]:
		usage()

	if play_cmd == "load":
		if not os.path.isfile(play_map):
			print("Map file does not exist\n")
			usage()
		with open(play_map, "rb") as inf:
			content = inf.read()
		play_map = base64.b64encode(content).decode()

	""" Setup Network """
	sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
	sock.connect((ip, port, 0, 0))

	window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, "The Lost Bottle")
	main_view = MyGame()
	main_view.setup(sock)

	val = communicate(sock, {"type": "HELO", "cmd": play_cmd, "map": play_map})

	main_view.enter_room(val["room"], val["pos"])

	window.show_view(main_view)
	arcade.run()

