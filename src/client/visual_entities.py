from common.entities import *
from client.game_config import *

import arcade

class VisRoom(Room):
	__slots__ = [
		"backImg",
		"background_list", # background
		"block_list", # blocks movement
		"free_list", # does not block movement,
		"scale"
	]

	def __init__(self, json):
		super().__init__("NoName", None)
		self.parse(json)
		w = self.w
		h = self.h
		
		# setup sprites etc.
		self.background_list = arcade.SpriteList()
		self.block_list = arcade.SpriteList()
		self.free_list = arcade.SpriteList()

		# backgorund
		island = arcade.Sprite("assets/sand.png", SCALE)
		island.width = BLOCK_SIZE * (self.w-4) * SCALE
		island.height = BLOCK_SIZE * (self.h-4) * SCALE
		island.left = 2 * BLOCK_SCALED
		island.bottom = 2 * BLOCK_SCALED
		self.background_list.append(island)
		top = arcade.Sprite("assets/shore.png", SCALE * 128 / 300)
		top.width = (self.w-4) * BLOCK_SCALED
		top.height = BLOCK_SCALED
		top.left = 2 * BLOCK_SCALED
		top.bottom = (self.h - 2) * BLOCK_SCALED
		self.background_list.append(top)
		top = arcade.Sprite("assets/shore.png", SCALE * 128 / 300, flipped_vertically = True)
		top.width = (self.w-4) * BLOCK_SCALED
		top.height = BLOCK_SCALED
		top.left = 2 * BLOCK_SCALED
		top.bottom = 1 * BLOCK_SCALED
		self.background_list.append(top)
		top = arcade.Sprite("assets/shore.png", SCALE * 128 / 300, flipped_diagonally = True)
		top.width = BLOCK_SCALED
		top.height = (self.h - 4) * BLOCK_SCALED
		top.left = 1 * BLOCK_SCALED
		top.bottom = 2 * BLOCK_SCALED
		self.background_list.append(top)
		top = arcade.Sprite("assets/shore.png", SCALE * 128 / 300, flipped_diagonally = True, flipped_horizontally = True)
		top.width = BLOCK_SCALED
		top.height = (self.h - 4) * BLOCK_SCALED
		top.left = (self.w - 2) * BLOCK_SCALED
		top.bottom = 2 * BLOCK_SCALED
		self.background_list.append(top)
		corner = arcade.Sprite("assets/shore_corner.png", SCALE * 128 / 300)
		corner.left = 1 * BLOCK_SCALED
		corner.bottom = 1 * BLOCK_SCALED
		self.background_list.append(corner)
		corner = arcade.Sprite("assets/shore_corner.png", SCALE * 128 / 300, flipped_diagonally = True, flipped_vertically = True)
		corner.left = (self.w - 2) * BLOCK_SCALED
		corner.bottom = 1 * BLOCK_SCALED
		self.background_list.append(corner)
		corner = arcade.Sprite("assets/shore_corner.png", SCALE * 128 / 300, flipped_vertically = True)
		corner.left = 1 * BLOCK_SCALED
		corner.bottom = (self.h - 2) * BLOCK_SCALED
		self.background_list.append(corner)
		corner = arcade.Sprite("assets/shore_corner.png", SCALE * 128 / 300, flipped_horizontally = True, flipped_vertically = True)
		corner.left = (self.w - 2) * BLOCK_SCALED
		corner.bottom = (self.h - 2) * BLOCK_SCALED
		self.background_list.append(corner)
		
		for e in self.exits:
			ex = self.exits[e]
			if ex["open"]:
				sprite_list = self.free_list
				door = arcade.Sprite("assets/ship.png", SCALE * 128 / 80)
			else:
				sprite_list = self.free_list
				door = arcade.Sprite("assets/shipunready.png", SCALE * 128 / 80)
			ex["sprite"] = door
			door.center_x = e[0] * BLOCK_SCALED + 0.5 * BLOCK_SCALED
			door.center_y = e[1] * BLOCK_SCALED + 0.5 * BLOCK_SCALED
			door.scale *= 1.2
			sprite_list.append(door)

		# Blocks around
		all_x = [x for x in range(w)]*2 + [0]*(h-2) + [w-1]*(h-2)
		all_y = [0] * w + [h-1] * w + [y for y in range(1, h-1)]*2
		for x, y in zip(all_x, all_y):
			# exits have a small outside standing block to prevent escaping from the room
			if (x, y) in self.exits:
				wall = arcade.Sprite("assets/block.png", SCALE)
				wall.alpha = 0
				wall.left = x * BLOCK_SCALED
				wall.bottom = y * BLOCK_SCALED
				if x == 0:
					wall.left -= BLOCK_SCALED / 2.0
				elif x == w-1:
					wall.left += BLOCK_SCALED / 2.0
				elif y == 0:
					wall.bottom -= BLOCK_SCALED / 2.0
				elif y == h-1:
					wall.bottom += BLOCK_SCALED / 2.0
				self.block_list.append(wall)
				#continue
			# normal border block
			wall = arcade.Sprite("assets/block.png", SCALE)
			wall.left = x * BLOCK_SCALED
			wall.bottom = y * BLOCK_SCALED
			wall.alpha = 0
			self.block_list.append(wall)

		# Additional Blocks
		for bl in json["blocks"]:
			for x, y in bl["pos"]:
				wall = arcade.Sprite(bl["img"], SCALE)
				wall.left = x * BLOCK_SCALED
				wall.bottom = y * BLOCK_SCALED
				self.block_list.append(wall)
				bl["sprite"] = wall
				self.blocks[(x, y)] = bl

		# Elements
		for k, el in json["elements"].items():
			self.elements[(el["x"], el["y"])] = VisElement(el, self)
			self.elements[(el["x"], el["y"])].update_state()

		# Load the background image for this level.
		self.backImg = arcade.load_texture("assets/water.png")

	def draw(self):
		self.background_list.draw()
		self.block_list.draw()
		self.free_list.draw()
		for k, el in self.elements.items():
			el.draw()

class VisElement(Element):
	__slots__ = [
		"sprite",
		"room"
	]

	def __init__(self, json, room):
		super().__init__()
		self.parse(json)
		self.room = room
		er = ELEMENT_TYPES[self.id]
		spr = arcade.Sprite(er["img"], SCALE)
		spr.left = self.x * BLOCK_SCALED
		spr.bottom = self.y * BLOCK_SCALED
		self.sprite = spr
		self.room.free_list.append(spr)
	
	def draw(self):
		if self.id == ELEMENT_SIGN:
			arcade.draw_text(self.value,
				(0.5+self.x) * BLOCK_SCALED,
				(1+self.y) * BLOCK_SCALED,
				arcade.color.BLACK,
				font_size=10,
				font_name=FONT,
				align="center",
				anchor_x="center",
				anchor_y="top")
	
	def update_state(self):
		if self.id == ELEMENT_BARREL:
			if self.value == "broken":
				spr = self.sprite
				self.room.free_list.remove(spr)
				spnew = arcade.Sprite("assets/barrel_open.png", SCALE)
				spnew.left = self.x * BLOCK_SCALED
				spnew.bottom = self.y * BLOCK_SCALED
				self.sprite = spnew
				self.room.free_list.append(spnew)
		elif self.id == ELEMENT_BOTTLE:
			if self.value == "empty":
				spr = self.sprite
				self.room.free_list.remove(spr)
				spnew = arcade.Sprite("assets/bottle_empty.png", SCALE)
				spnew.left = self.x * BLOCK_SCALED
				spnew.bottom = self.y * BLOCK_SCALED
				self.sprite = spnew
				self.room.free_list.append(spnew)
