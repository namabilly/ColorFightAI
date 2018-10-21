# You need to import colorfight for all the APIs
import colorfight
import random
import math

# Strategies
# 1. Go for the energy cell
# 2. Go for the gold cell
# 3. Greedy expand
# 4. Select move with least neighbors
# 5. Go for the base!
# 6. Self defense

# TODO: Use skills
# things can be done each turn:
# 	attack: ?s
# 	defend: ?s
# 	build base: 60g, 30s
# 	blastattack: 30e 
# 	blastdefend: 40g, 40e, not available in this version
# 	multiattack: 40g, considered later
# 	boost: 15e

class NamabillyAI:
	
	directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
	ENERGY_ENABLED = False
	BASE_ENABLED = False
	
	def __init__(self):
		self.g = colorfight.Game()
		self.isJoined = self.g.JoinGame('namabilly')
		self.my_cell = []
		self.neighbor_cell = []
		self.border_cell = []
		self.my_base = []
		self.energy_cell = [] # 18
		self.gold_cell = [] # 18
		self.enemy_base = []
		self.neighbor_enemy = []
		self.target = []
		self.modes = ["energy", "gold", "fast", "safe", "attack", "defend"]
		self.status = {
			'energy': 0,
			'energyGrowth': 0,
			'gold': 0,
			'goldGrowth': 0,
			'cellNum': 1,
			'baseNum': 1,
			'cdTime': 0,
			'isDangerous': False,
			'isTaking': False,
			'mode': 0
		}
		self.graph = []
		self.gr = []
		self.path = []
		
	def run(self):
		if self.isJoined:
			# get energy/gold cells
			for x in range(self.g.width):
				for y in range(self.g.height):
					c = self.g.GetCell(x, y)
					if c.cellType == 'energy':
						self.energy_cell.append((x, y))
					elif c.cellType == 'gold':
						self.gold_cell.append((x, y))
						
			# initialize graph
			self.init_graph()
			
			while True:
				# do stuff
				self.g.Refresh()
				self.update()
				print(self.status)
				if not self.status['isTaking']:
					self.move()
					cell = self.target[0]
					print(self.g.AttackCell(cell[0], cell[1]))
					self.status['isTaking'] = True
		else:
			print("Failed to join game!")
	
	def update(self):
		
		# update my cells & enemy bases
		self.my_cell = []
		self.enemy_base = []
		for x in range(self.g.width):
			for y in range(self.g.height):
				c = self.g.GetCell(x, y)
				if c.owner == self.g.uid:
					self.my_cell.append((x, y))
				elif c.isBase:
					self.enemy_base.append((x, y))
		
		# update my bases
		self.my_base = []
		for cell in self.my_cell:
			if self.g.GetCell(cell[0], cell[1]).isBase:
				self.my_base.append(cell)
		
		# update neighbors & borders & enemy type
		self.neighbor_cell = []
		self.border_cell = []
		self.neighbor_enemy = []
		for cell in self.my_cell:
			x, y = cell
			for d in self.directions:
				c = self.g.GetCell(x+d[0], y+d[1])
				if c != None:
					if c.owner != self.g.uid:
						if c not in self.neighbor_cell:
							self.neighbor_cell.append((x+d[0], y+d[1]))
						if c.owner not in self.neighbor_enemy and c.owner != 0:
							self.neighbor_enemy.append(c.owner)
						if cell not in self.border_cell:
							self.border_cell.append(cell)
					if self.g.GetCell(x, y).isTaking:
						if (x+d[0], y+d[1]) in self.my_cell and (x+d[0], y+d[1]) not in self.border_cell:
							self.border_cell.append((x+d[0], y+d[1]))
		
		# update status
		diff = self.g.energy - self.status['energy']
		if diff >= 0:
			self.status['energyGrowth'] = diff
		self.status['energy'] = self.g.energy
		diff = self.g.gold - self.status['gold']
		if diff >= 0:
			self.status['goldGrowth'] = diff
		self.status['gold'] = self.g.gold
		self.status['cellNum'] = self.g.cellNum
		self.status['baseNum'] = self.g.baseNum if self.BASE_ENABLED else 0
		self.status['cdTime'] = self.g.cdTime
		if self.g.currTime > self.status['cdTime']:
			self.status['isTaking'] = False
		else:
			self.status['isTaking'] = True
		self.status['isDangerous'] = False
		# danger status; needs to be fixed
		if self.status['baseNum'] == 1:
			base = self.my_base[0]
			dangerLevel = 0
			for d in self.directions:
				c = self.g.GetCell(base[0]+d[0], base[1]+d[1])
				if c != None:
					if c.owner != self.g.uid and c.owner != 0:
						dangerLevel += 1
			if dangerLevel >= 2:
				self.status['isDangerous'] = True

		# update mode
		if self.status['isDangerous']:
			self.status['mode'] = 5
		elif self.ENERGY_ENABLED and self.status['energyGrowth'] < 0.3:
			self.status['mode'] = 0
		elif self.g.goldCellNum < 1:
			self.status['mode'] = 1
		elif self.status['cellNum'] < 100:
			self.status['mode'] = 2
		elif self.status['cellNum'] < 200:
			self.status['mode'] = 3
		else:
			self.status['mode'] = 4
		
		# test
		# self.status['mode'] = 1
		
		# get target
		self.get_target()
	
	def get_neighbors(self, cells):
		neighbors = []
		for cell in cells:
			for d in self.directions:
				if 0 <= cell[0]+d[0] < self.g.width and 0 <= cell[1]+d[1] < self.g.height:
					if (cell[0]+d[0], cell[1]+d[1]) not in neighbors:
						neighbors.append((cell[0]+d[0], cell[1]+d[1]))
		return neighbors
	
	def get_target(self):
		self.target = []
		# mode 0 - energy
		# needs graph, shortest path
		if self.modes[self.status['mode']] == "energy":
			self.dijkstra("energy")
			ver = None
			if self.path:
				ver = self.path.pop()
			if ver:
				self.target.append((ver.x, ver.y))
			else:
				self.update()
		# mode 1 - gold
		# shortest path
		elif self.modes[self.status['mode']] == "gold":
			self.dijkstra("gold")
			ver = None
			if self.path:
				ver = self.path.pop()
			if ver:
				self.target.append((ver.x, ver.y))
			else:
				self.update()
		# mode 2 - fast
		# greedy expand
		# assign value to neighbor cells, choose the highest one, i.e. shorter time and better benefit
		elif self.modes[self.status['mode']] == "fast":
			neighborCell = []
			for cell in self.neighbor_cell:
				neighborCell.append(self.g.GetCell(cell[0], cell[1]))
			neighborCell.sort(key = self.get_val_corner, reverse = True)
			for cell in neighborCell:
				if not cell.isTaking:
					self.target.append((cell.x, cell.y))
					break
			else:
				self.target.append(neighborCell[0].x, neighborCell[0].y)
		# mode 3 - safe
		# now you want to play safe
		# choose the move to minimize type of neighbors
		elif self.modes[self.status['mode']] == "safe":
			neighborCell = []
			for cell in self.neighbor_cell:
				neighborCell.append(self.g.GetCell(cell[0], cell[1]))
			neighborCell.sort(key = self.get_val, reverse = True)
			for cell in neighborCell:
				if not cell.isTaking:
					isSafe = True
					for d in self.directions:
						c = self.g.GetCell(cell.x+d[0], cell.y+d[1])
						if c != None:
							if c.owner in self.neighbor_enemy or c.owner == 0 or c.owner == self.g.uid:
								isSafe = True
							else:
								isSafe = False
								break
					if isSafe:
						self.target.append((cell.x, cell.y))
						break
			else:
				self.target.append((neighborCell[0].x, neighborCell[0].y))
		# mode 4 - attack
		# get rid of other players!
		elif self.modes[self.status['mode']] == "attack":
			self.status['mode'] = 3
			self.get_target()
		# mode 5 - defend
		# not too much of a concern now
		elif self.modes[self.status['mode']] == "defend":
			self.status['mode'] = 2
			self.get_target()
		else:
			print("Error: mode not defined.")
			
	def get_val(self, cell):
		take_time = cell.takeTime
		if take_time < 0:
			return 0
		neighborNum = 0
		type = cell.cellType
		val = 1
		if type == 'gold':
			val = 10
		elif type == 'energy':
			val = 3
		else:
			val = 1
		for d in self.directions:
			c = self.g.GetCell(cell.x+d[0], cell.y+d[1])
			if c != None:
				if c.owner == self.g.uid:
					neighborNum += 1
		return val / ((take_time * min(1, 1 - 0.25*(neighborNum - 1))) / (1 + self.status['energy']/200.0))
		
	def map_corner(self, cell):
		x = cell.x
		y = cell.y
		valX = abs(x - (self.g.width-1)/2)
		valY = abs(y - (self.g.height-1)/2)
		return (valX / (self.g.width/2))**2 + (valY / (self.g.height/2))**2
	
	def get_val_corner(self, cell):
		return self.map_corner(cell) * self.get_val(cell)
	
	def get_take_time(self, cell):
		take_time = cell.takeTime
		if take_time < 0:
			return math.inf
		neighborNum = 0
		for d in self.directions:
			c = self.g.GetCell(cell.x+d[0], cell.y+d[1])
			if c != None:
				if c.owner == self.g.uid:
					neighborNum += 1
		return take_time * min(1, 1 - 0.25*(neighborNum - 1)) / (1 + self.status['energy']/200.0)
		
	def move(self):
		# build base - 60g, 30s
		if self.BASE_ENABLED:
			if self.status['baseNum'] < 3:
				if self.status['gold'] > 60:
					if self.status['baseNum'] < 2:
						if self.status['cellNum'] > 30:
							random.shuffle(self.my_cell)
							for cell in self.my_cell:
								if cell not in self.border_cell and cell not in self.my_base\
								and cell not in self.get_neighbors(self.my_base):
									if not self.g.GetCell(cell[0], cell[1]).isTaking:
										self.g.BuildBase(cell[0], cell[1])
					elif self.status['cellNum'] > 50:
						for cell in self.my_cell:
							if cell not in self.border_cell and cell not in self.my_base\
							and cell not in self.get_neighbors(self.my_base):
								if not self.g.GetCell(cell[0], cell[1]).isTaking:
									self.g.BuildBase(cell[0], cell[1])
		
		# reinforce border
		if self.status['mode'] != 0 and self.status['mode'] != 1 and len(self.border_cell) < 40:
			for cell in self.border_cell:
				c = self.g.GetCell(cell[0], cell[1])
				for d in self.directions:
					cc = self.g.GetCell(cell[0]+d[0], cell[1]+d[1])
					if cc != None:
						if cc.owner != 0 and cc.owner != self.g.uid: 
							if 1 < c.takeTime < 4:
								print(self.g.AttackCell(cell[0], cell[1]))
								self.update()
								self.g.Refresh()	
								break
			
		return

	def init_graph(self):
		self.graph = []
		self.gr = [[Vertex(0, 0, 0) for i in range(self.g.width)] for j in range(self.g.height)]
		# the graph
		for x in range(self.g.width):
			for y in range(self.g.height):
				v = Vertex(x, y, 0)
				self.gr[x][y] = v
				self.graph.append(v)
		# add successor
		for x in range(self.g.width):
			for y in range(self.g.height):
				for d in self.directions:
					if 0 <= x+d[0] < self.g.width and 0 <= y+d[1] < self.g.height:
						self.gr[x][y].add_successor(self.gr[x+d[0]][y+d[1]])
		
	def refresh_graph(self):
		for x in range(self.g.width):
			for y in range(self.g.height):
				c = self.g.GetCell(x, y)
				self.gr[x][y].val = self.get_take_time(c)
				self.gr[x][y].dist = math.inf
				self.gr[x][y].preBest = None
		
	def dijkstra(self, tar):
		self.refresh_graph()
		search_set = []
		searched_set = []
		# source = []
		target = []
		targets = []
		for cell in self.border_cell:
			self.gr[cell[0]][cell[1]].dist = 0
			search_set.append(self.gr[cell[0]][cell[1]])
		
		if tar == 'energy':
			target = self.energy_cell
		elif tar == 'gold':
			target = self.gold_cell
		elif tar == 'base':
			target = self.enemy_base
		else:
			print("Error: invalid target!")
			return
		
		for cell in target:
			if cell not in self.my_cell:
				targets.append(self.gr[cell[0]][cell[1]])
		
		v = Vertex(-1, 0, 0)
		
		while (search_set):
			min = math.inf
			for ver in search_set:
				if ver.dist < min:
					min = ver.dist
					v = ver
			search_set.remove(v)
			searched_set.append(v)
			if v in targets:
				break
			for ver in v.successor:
				if ver not in searched_set and (ver.x, ver.y) not in self.my_cell:
					if ver not in search_set:
						search_set.append(ver)
					c = v.dist + ver.val
					if ver.dist > c:
						ver.dist = c
						ver.preBest = v
		self.path = []
		while(v.preBest):
			self.path.append(v)
			v = v.preBest
		self.path.reverse()
		
						
class Vertex:
	
	def __init__(self, x, y, val):
		self.x = x
		self.y = y
		self.val = val # cost
		self.dist = math.inf
		self.successor = []
		self.preBest = None

	def add_successor(self, v):
		self.successor.append(v)
	
	def get_successor(self):
		return self.successor
		
	def __str__(self):
		return str(self.x)+" "+str(self.y)+" "+str(self.val)+" "+str(self.dist)
	
	
if __name__ == '__main__':
	ai = NamabillyAI()
	ai.run()

	