import random
import subprocess
import string

def gen_name(x = 10, y = 15):
	length = random.randint(x, y)
	return "".join(random.choice(string.ascii_letters) for _ in range(length))

# should always print 1 / ..., because we don't shuffle the first
def bottlecheck(bs, target, num = 10000):
	ids = list(range(len(bs)))
	yes = 0
	for _ in range(num):
		y = 0
		for i in ids:
			percent, volume = bs[i]
			y = (y * (4 - volume) + percent * volume) / 4
			if y >= target:
				yes += 1
				break
		random.shuffle(ids)
	print(f">> {yes}\t/ {num}")
	if yes > 2:
		print(sorted(bs))

class Room:
	def __init__(self, saveable, large = False):
		if large:
			self.w = random.randint(15, 20)
			self.h = random.randint(15, 20)
		else:
			self.w = random.randint(5, 20)
			self.h = random.randint(5, 20)
		self.name = gen_name(20, 30)
		self.saveable = saveable
		self.exits = []
		self.blocks = []
		self.elements = {}
		self.spaces = [ # 1. dimension is x (right) !
			[None] * self.h
			for _ in range(self.w)
		]
		self.fill_blocks()
		self.fill_barrels()
	
	def fill_blocks(self):
		objs = [
			":resources:/images/tiles/cactus.png",
			":resources:/images/tiles/bush.png",
			":resources:/images/tiles/rock.png",
			":resources:/images/space_shooter/meteorGrey_big3.png"
		]
		poss = [[] for _ in range(len(objs))]
		
		self.blocks = []
		m = self.h // 2
		for i in range(2, self.w - 2):
			if random.randint(0, 2) == 0:
				r = random.randint(0, len(objs) - 1)
				if r < len(objs):
					poss[r] += [[i, m]]
					self.spaces[i][m] = "block"
		for i in range(len(objs)):
			if len(poss[i]) > 0:
				self.blocks += [{"img": objs[i], "pos": poss[i]}]

	def fill_barrels(self):
		bc = random.randint(0, 5)
		for _ in range(bc):
			self.add_element(gen_name(5, 10), {
				"id": 4,
				"value": random.choice(["intact"] * 5 + ["broken"])
			})

	def add_element(self, uuid, el):
		if uuid in self.elements:
			print("FAIL duplicate uuid")
		el["x"], el["y"] = self.free_pos("element")
		self.elements[uuid] = el
		return el
	
	def free_pos(self, fill_with):
		tries = 0
		while tries < self.w * self.h * 3:
			x = random.randint(1, self.w - 2)
			y = random.randint(1, self.h - 2)
			if not self.spaces[x][y]:
				self.spaces[x][y] = fill_with
				return x, y
		print("FAIL no empty spaces")
		return None

	def find_exit(self):
		tries = 0
		while tries < 50:
			if random.randint(0, 1) == 0: # sides
				x = random.choice([0, self.w - 1])
				y = random.randint(1, self.h - 2)
			else: # top/bot
				x = random.randint(1, self.w - 2)
				y = random.choice([0, self.h - 1])
			if not self.spaces[x][y]:
				return (x, y)
		print("Failed")
		return (1, 0)
	
	def add_exit(self, pos, other, otherpos, pwd):
		ox, oy = otherpos
		if ox == 0:
			ox = 1
		elif oy == 0:
			oy = 1
		elif ox == other.w - 1:
			ox = other.w - 2
		else:
			oy = other.h - 2
		self.exits += [{
			"x": pos[0],
			"y": pos[1],
			"room": other.name,
			"targetx": ox,
			"targety": oy,
			"open": True,
			"keypad": pwd
		}]
		self.spaces[pos[0]][pos[1]] = "exit"
	
	def dump(self):
		return self.name, {
			"w": self.w,
			"h": self.h,
			"saveable": self.saveable,
			"background": "cave.png",
			"exits": self.exits,
			"blocks": self.blocks,
			"elements": self.elements
		}

class Graph:
	def __init__(self, n):
		self.n = n
		
		self.parent = [i for i in range(n)] # union-find
		self.groups = n
		
		self.edges = []
		
		self._marks = [[] for _ in range(n)] # for debug only
	
	def find(self, a):
		if self.parent[a] != a:
			self.parent[a] = self.find(self.parent[a])
		return self.parent[a]

	def union(self, a, b):
		a = self.find(a)
		b = self.find(b)
		if a == b:
			return
		self.parent[a] = b
		self.groups -= 1

	def randomfill(self):
		# make connected
		while self.groups > 1:
			a = random.randint(0, self.n-1)
			b = random.randint(0, self.n-1)
			if a == b:
				continue
			if a > b:
				a, b = b, a
			if (a, b) in self.edges:
				continue
			self.edges += [(a, b)]
			self.union(a, b)
	
	def find_path(self, start, end, cur):
		if start == end:
			return cur + [end]
		for a, b in self.edges:
			if b == start:
				a, b = b, a
			if a == start:
				if not b in cur:
					p = self.find_path(b, end, cur + [start])
					if p:
						return p
		return None
	
	def to_dot(self):
		s = "graph {\n"
		for a, b in self.edges:
			s += f"a{a} -- a{b};\n"
		for ni in range(self.n):
			if len(self._marks[ni]) > 0:
				s += f"a{ni}[label=\"{ni}|" + "|".join(self._marks[ni]) + "\"];\n"
		s += "}\n"
		return s
	
	def _marknode(self, ni, s):
		self._marks[ni] += [s]

def add_edge(a, b, pwd = None): # rooms a, b
	ea = a.find_exit()
	eb = b.find_exit()
	a.add_exit(ea, b, eb, pwd)
	b.add_exit(eb, a, ea, None)

"""
target := % value to achieve for success
"""
def gen_bottles(target):
	bottles = []
	for i in range(random.randint(15, 22)): # never enough
		bottles += [(random.randint(0, target - 1), random.randint(1, 2))]
	bottles = list(sorted(bottles))
	cur = 0
	for i in range(len(bottles)):
		cur = drink(cur, bottles[i][1], bottles[i][0])
	while cur < target + 0.0001: # just in case
		# use v = 2 as many as needed
		v = 2
		p = int(2 * (target - cur) + cur) + 1
		if p > 99:
			p = target # small percent that makes enough progress to eventually terminate
		bottles += [(p, v)]
		cur = drink(cur, v, p)
	return bottles

def drink(oldpercent, volume, percent):
	return (oldpercent * (4 - volume) + percent * volume) / 4

# input: list of room ids
# output: list of exits to use (including keypad)
def path_to_exits(rooms, path):
	p = []
	for i in range(1, len(path)):
		for e in rooms[path[i-1]].exits:
			if e["room"] == rooms[path[i]].name:
				p += [(e["x"], e["y"], e["keypad"])]
				break
		else:
			raise RuntimeError("Failed converting path to exit sequence")
	return p

dreamlist = [
	"You become relaxed and dream of an island far far away with a hidden treasure...",
	"There is a giant owl behind you. You turn around and it vanished...",
	"Digging for a treasure you unveil an old artifact. However, it is useless...",
	"Life is beautiful. You are on your own island filled with wildlife and listen to the singing of birds above you..."
]

def gen_map(flag = "INSERT FLAG", check_bottles = False, num = 10000):
	g1 = Graph(random.randint(3, 7))
	g1.randomfill()
	
	g2 = Graph(random.randint(3, 7))
	g2.randomfill()
	
	rooms = []
	bottleroomid = random.randint(0, g1.n - 1) # need this one large
	for i in range(g1.n):
		rooms += [Room(True, large = (i == bottleroomid))]
	for a, b in g1.edges:
		add_edge(rooms[a], rooms[b])

	for i in range(g2.n):
		rooms += [Room(False)]
	for a, b in g2.edges:
		add_edge(rooms[a+g1.n], rooms[b+g1.n])
	a = random.randint(0, g1.n-1)
	b = g1.n + random.randint(0, g2.n - 1)
	add_edge(rooms[a], rooms[b], pwd = gen_name(8, 8))

	starterid = random.randint(0, g1.n-1)
	targetroomid = g1.n + random.randint(0, g2.n-1)

	starter = rooms[starterid]
	bottleroom = rooms[bottleroomid]
	
	signpath = g1.find_path(starterid, a, []) + [g1.n + x for x in g2.find_path(b - g1.n, targetroomid - g1.n, [])]
	# debugging
	if False:
		g1._marknode(starterid, "start")
		g1._marknode(a, "portal")
		g1._marknode(bottleroomid, "bottles")
		with open("/tmp/a.dot", "w") as outf:
			outf.write(g1.to_dot())
		r = subprocess.check_output([
			"dot",
			"-Tpdf",
			"/tmp/a.dot"
			])
		with open("/tmp/a.pdf", "wb") as outf:
			outf.write(r)
	signpath = path_to_exits(rooms, signpath)
	bottlepath = g1.find_path(starterid, bottleroomid, [])
	bottlepath = path_to_exits(rooms, bottlepath)
	# sign
	sign = rooms[targetroomid].add_element(
		gen_name(10, 15),
		{
			"id": 1,
			"value": flag
		})

	# bottles
	target = random.randint(70, 85)
	bottles = gen_bottles(target)
	bottleorder = []
	for b in bottles:
		e = bottleroom.add_element(
			gen_name(10, 15),
			{
				"id": 5,
				"value": "{}|{}%".format(b[1], b[0])
			})
		bottleorder += [(e["x"], e["y"])]
	
	# shuffle bottle order in dictionary
	bottlelist = [(k, bottleroom.elements[k]) for k in bottleroom.elements]
	random.shuffle(bottlelist)
	bottleroom.elements = {k : v for k, v in bottlelist}
	if check_bottles:
		bottlecheck(bottles, target, num)
	

	# map
	roomdict = {}
	for r in rooms:
		n, d = r.dump()
		roomdict[n] = d
	startx, starty = starter.free_pos("start")
	m = {
		"rooms": roomdict,
		"globals": {
			"posx": startx,
			"posy": starty,
			"room": starter.name
		},
		"dreams": []
	}
	targets = list(sorted([random.randint(0, 70) for _ in range(2)]))
	for t in targets:
		m["dreams"] += [[t, random.choice(dreamlist)]]
	m["dreams"] += [[target, "You start to hallucinating about the meaning of life and start to beliebe that the answer to life is " + flag]]
		
		
	
	# debugging
	if False:
		with open("/tmp/a.dot", "w") as outf:
			outf.write(g1.to_dot())
		r = subprocess.check_output([
			"dot",
			"-Tpdf",
			"/tmp/a.dot"
			])
		with open("/tmp/a.pdf", "wb") as outf:
			outf.write(r)
	
	return {
		"map": m,
		"signpos": (sign["x"], sign["y"]),
		"signpath": signpath,
		"bottlepath": bottlepath,
		"bottleorder": bottleorder
	}

## just for test generation
# check_bottles := checks how easy it is to brute force bottle order
def gen_test(check_bottles = False, num = 10000):
	import json
	for i in range(100):
		d = gen_map("FAUST_" + "".join(random.choice(string.ascii_lowercase) for _ in range(10)), check_bottles, num)
		d["map"]["map"] = "testmaps/m_%d.json" % i
		with open("testmaps/m_%d.json" % i, "w") as outf:
			json.dump(d["map"], outf, indent='\t')

if __name__ == "__main__":
	import sys
	if len(sys.argv) > 1 and sys.argv[1] in ["brute", "check"]:
		if len(sys.argv) > 2:
			num = int(sys.argv[2])
		else:
			num = 10000
		gen_test(True, num)
	else:
		gen_test(False)
