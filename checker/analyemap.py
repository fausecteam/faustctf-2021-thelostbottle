import sys
import json

with open(sys.argv[1]) as inf:
	j = json.load(inf)

for r in j["rooms"]:
	room = j["rooms"][r]
	bottles = []
	for e in room["elements"]:
		el = room["elements"][e]
		if el["id"] == 5:
			bottles += [el["value"].split("|") + [el["x"], el["y"]]]
			# swap order for sorting
			bottles[-1][0], bottles[-1][1] = int(bottles[-1][1].replace("%", "")), int(bottles[-1][0])
	# drink
	if len(bottles) > 0:
		bottles.sort()
		y = 0
		for percent, volume, px, py in bottles:
			print(f"pos: {px}/{py},\t{percent}%, {volume} l")
			y = (y * (4 - volume) + percent * volume) / 4
			print(y)
		print(f"--> {y} % / {j['dreams'][-1][0]}")
