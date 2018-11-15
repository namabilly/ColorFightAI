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
	surroundings = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
	horizontal = [(-4, 0), (-3, 0), (-2, 0), (-1, 0), (1, 0), (2, 0), (3, 0), (4, 0)]
	vertical = [(0, -4), (0, -3), (0, -2), (0, -1), (0, 1), (0, 2), (0, 3), (0, 4)]
	multi = [(-2, 0), (-1, 1), (-1, -1), (0, 2), (0, -2), (1, 1), (1, -1), (2, 0)]
	ENERGY_ENABLED = True
	BASE_ENABLED = True
	BLAST_ENABLED = True
	MULTIATTACK_ENABLED = True
	GOLD_FAC = 11
	ENERGY_FAC = 3
	
	def __init__(self):
		self.g = colorfight.Game()
		self.isJoined = self.g.JoinGame('namabilly2')
		self.my_cell = []
		self.neighbor_cell = []
		self.border_cell = []
		self.my_base = []
		self.energy_cell = [] # 18
		self.gold_cell = [] # 18
		self.my_energy = []
		self.my_gold = []
		self.enemy_base = []
		self.neighbor_enemy = []
		self.on_enemy = 0
		self.on_enemy_cell = []
		self.on_enemy_base = []
		self.on_enemy_base_round = []
		self.getBaseRound = False
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
		
		# skill content
		
		# blast
		self.blast_mode = 0
		# 0: square
		# 1: horizontal
		# 2: vertical
		self.neighbor_count = [[0]*3 for c in range(self.g.width*self.g.height)]
		
		# multiattack
		self.multi_points = []
		
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
				self.update()
				print(self.status)
				if not self.status['isTaking']:
					self.get_target()
					self.move()
					if self.target:
						cell = self.target[0]
						c = self.g.GetCell(cell[0], cell[1])
						if self.MULTIATTACK_ENABLED:
							if self.status['baseNum'] == 3 and self.status['gold'] >= 40:
								val = self.get_val(c)
								for d in self.directions:
									point = (cell[0]+d[0], cell[1]+d[1])
									if self.get_multi_val(point) > val:
										print(self.g.MultiAttack(point[0], point[1]))
										self.update()
										break
						print(str(cell[0])+" "+str(cell[1]))
						print(self.g.AttackCell(cell[0], cell[1], self.boost(c)))
		else:
			print("Failed to join game!")
	
	def update(self):
	
		# refresh from server
		self.g.Refresh()
		
		# update my cells & enemy bases & on enemy cell
		self.my_cell = []
		self.enemy_base = []
		self.on_enemy_cell = []
		for x in range(self.g.width):
			for y in range(self.g.height):
				c = self.g.GetCell(x, y)
				if c.owner == self.g.uid:
					self.my_cell.append((x, y))
				elif c.isBase and not c.isTaking:
					self.enemy_base.append((x, y))
				if self.on_enemy != 0 and c.owner == self.on_enemy:
					self.on_enemy_cell.append((x, y))
		if not self.on_enemy_cell:
			self.on_enemy = 0
		# update on enemy base IMPORTANT when the target moves by accident
		self.on_enemy_base = []
		if self.on_enemy != 0:
			for cell in self.enemy_base:
				if cell in self.on_enemy_cell:
					self.on_enemy_base.append(cell)
		else:
			self.on_enemy_base = self.enemy_base
		
		# update my bases, energys, and golds
		self.my_base = []
		self.my_energy = []
		self.my_base = []
		for cell in self.my_cell:
			if self.g.GetCell(cell[0], cell[1]).isBase:
				self.my_base.append(cell)
			if cell in self.energy_cell:
				self.my_energy.append(cell)
			elif cell in self.gold_cell:
				self.my_gold.append(cell)
		
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
		
		# update blast info
		self.neighbor_count = [[0]*3 for c in range(self.g.width*self.g.height)]
		for cell in self.my_cell:
			for s in self.surroundings:
				cc = self.g.GetCell(cell[0]+s[0], cell[1]+s[1])
				if cc != None:
					if cc.owner != self.g.uid and cc.owner != 0:
						self.neighbor_count[cell[0]+s[0]+cell[1]+s[1]*self.g.height][0] += 1
			for h in self.horizontal:
				cc = self.g.GetCell(cell[0]+h[0], cell[1]+h[1])
				if cc != None:
					if cc.owner != self.g.uid and cc.owner != 0:
						self.neighbor_count[cell[0]+s[0]+cell[1]+s[1]*self.g.height][1] += 1
			for v in self.vertical:
				cc = self.g.GetCell(cell[0]+v[0], cell[1]+v[1])
				if cc != None:
					if cc.owner != self.g.uid and cc.owner != 0:
						self.neighbor_count[cell[0]+s[0]+cell[1]+s[1]*self.g.height][2] += 1
		
		# update multi info
		self.multi_points = []
		for cell in self.neighbor_cell:
			for d in self.directions:
				if 0 <= cell[0]+d[0] < self.g.height and 0 <= cell[1]+d[1] < self.g.width:
					self.multi_points.append(cell)
		self.multi_points.sort(key = self.get_multi_val, reverse = True)
		
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
		print(self.status['isTaking'])
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
		elif self.ENERGY_ENABLED and self.status['energyGrowth'] < 0.3 and self.g.energyCellNum < 5:
			self.status['mode'] = 0
		elif self.g.goldCellNum < 3:
			self.status['mode'] = 1
		elif self.status['cellNum'] < 100:
			self.status['mode'] = 2
		elif self.status['cellNum'] < 150:
			self.status['mode'] = 3
		elif self.neighbor_enemy:
			self.status['mode'] = 4
		else:
			self.status['mode'] = 2
		
		# test
		# self.status['mode'] = 0
		# self.status['mode'] = 1
		# self.status['mode'] = 2
		# self.status['mode'] = 4
		
		# get target
		# self.get_target()
	
	def get_neighbors(self, cells):
		neighbors = []
		for cell in cells:
			for d in self.directions:
				if 0 <= cell[0]+d[0] < self.g.height and 0 <= cell[1]+d[1] < self.g.width:
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
				if self.status['isTaking']:
					self.get_target()
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
				if self.status['isTaking']:
					self.get_target()
		# mode 2 - fast
		# greedy expand
		# assign value to neighbor cells, choose the highest one, i.e. shorter time and greater benefit
		elif self.modes[self.status['mode']] == "fast":
			neighborCell = []
			for cell in self.neighbor_cell:
				neighborCell.append(self.g.GetCell(cell[0], cell[1]))
			neighborCell.sort(key = self.get_val_corner, reverse = True)
			for cell in neighborCell:
				if not cell.isTaking:
					if self.MULTIATTACK_ENABLED:
						if self.BASE_ENABLED and self.status['baseNum'] == 3:
							if self.status['gold'] >= 40:
								val = self.get_val(cell)
								point = self.multi_points[0]
								if val < self.get_multi_val(point):
									print(self.g.MultiAttack(point[0], point[1]))
									self.update()
									break
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
						if self.MULTIATTACK_ENABLED:
							if self.BASE_ENABLED and self.status['baseNum'] == 3:
								if self.status['gold'] >= 40:
									val = self.get_val(cell)
									point = self.multi_points[0]
									if val < self.get_multi_val(point):
										print(self.g.MultiAttack(point[0], point[1]))
										self.update()
										break
						self.target.append((cell.x, cell.y))
						break
			else:
				self.target.append((neighborCell[0].x, neighborCell[0].y))
		# mode 4 - attack
		# get rid of other players!
		elif self.modes[self.status['mode']] == "attack":
			# attack base - basic
			if self.on_enemy != 0:
				if self.on_enemy_base:
					for cell in self.on_enemy_base:
						if cell in self.neighbor_cell:
							self.on_enemy_base_round = []
							baseRoundCount = 0
							for d in self.directions:
								c = self.g.GetCell(cell[0]+d[0], cell[1]+d[1])
								if c != None:
									if c.owner == self.on_enemy:
										self.on_enemy_base_round.append((cell[0]+d[0], cell[1]+d[1]))
										baseRoundCount += 1
							if baseRoundCount <= 1:
								if self.on_enemy_base_round:
									if self.status['energy'] >= 40:
										round = self.on_enemy_base_round[0]
										diff = (cell[0]-round[0], cell[1]-round[1])
										type = "vertical" if diff[0] == 0 else "horizontal"
										atkP = self.g.GetCell(cell[0]+diff[0], cell[1]+diff[1])
										if atkP == None:
											atkP = self.g.GetCell(cell[0]+diff[1], cell[1]+diff[0])
											type = "square"
											if atkP == None:
												atkP = self.g.GetCell(cell[0]-diff[1], cell[1]-diff[0])
												type = "square"
											elif atkP.owner != self.g.uid:
												atkP = self.g.GetCell(cell[0]-diff[1], cell[1]-diff[0])
												type = "square"
										elif atkP.owner != self.g.uid:
											atkP = self.g.GetCell(cell[0]+diff[0]*2, cell[1]+diff[1]*2)
											if atkP == None:
												atkP = self.g.GetCell(cell[0]+diff[1], cell[1]+diff[0])
												type = "square"
												if atkP == None:
													atkP = self.g.GetCell(cell[0]-diff[1], cell[1]-diff[0])
													type = "square"
												elif atkP.owner != self.g.uid:
													atkP = self.g.GetCell(cell[0]-diff[1], cell[1]-diff[0])
													type = "square"
										print(self.g.Blast(atkP.x, atkP.y, type))
										self.on_enemy_base = []
										self.on_enemy_base_round = []
										self.update()
							if self.on_enemy_base_round and not self.g.GetCell(cell[0], cell[1]).isBuilding:
								self.getBaseRound = True
							else:
								self.getBaseRound = False
							break
			print(len(self.on_enemy_base_round))
			if not self.getBaseRound:
				self.dijkstra('base')
			else:
				self.dijkstra('base_round')
			ver = None
			if self.path:
				ver = self.path.pop()
			if ver:
				self.target.append((ver.x, ver.y))
				if ver.val >= 8 and not self.boost(self.g.GetCell(ver.x, ver.y)):
					# change target
					if self.neighbor_enemy:
						random.shuffle(self.neighbor_enemy)
						for enemy in self.neighbor_enemy:
							if enemy != self.on_enemy:
								self.on_enemy = enemy
								self.on_enemy_base = []
								for base in self.enemy_base:
									bc = self.g.GetCell(base[0], base[1])
									if bc.owner == self.on_enemy:
										self.on_enemy_base.append((base[0], base[1]))
								break
					self.update()
					self.status['mode'] = 3
					self.get_target()
			else:
				self.update()
				if self.status['isTaking']:
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
		type = cell.cellType
		val = 1
		if type == 'gold':
			val = self.GOLD_FAC
		elif type == 'energy':
			val = self.ENERGY_FAC
		else:
			val = 1
		return val / self.get_take_time(cell)
		
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
	
	def get_multi_val(self, point):
		count = 0
		time = 0
		for d in self.directions:
			cell = self.g.GetCell(point[0]+d[0], point[1]+d[1])
			fac = 1.0
			if cell != None:
				if (cell.x, cell.y) in self.neighbor_cell or (cell.x, cell.y) in self.my_cell:
					if cell.cellType == 'gold':
						fac = self.GOLD_FAC
					elif cell.cellType == 'energy':
						fac = self.ENERGY_FAC
					if cell.owner == self.g.uid:
						fac *= 1/4
					count += fac
					t = self.get_take_time(cell)
					if t > time:
						time = t
		if count <= 1:
			return -1
		return count / time
	
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
										print(self.g.BuildBase(cell[0], cell[1]))
										self.update()
										break
					elif self.status['cellNum'] > 50:
						random.shuffle(self.my_cell)
						for cell in self.my_cell:
							if cell not in self.border_cell and cell not in self.my_base\
							and cell not in self.get_neighbors(self.my_base):
								if not self.g.GetCell(cell[0], cell[1]).isTaking:
									print(self.g.BuildBase(cell[0], cell[1]))
									self.update()
									break
		
		# reinforce base
		if self.BASE_ENABLED:
			if self.my_base:
				for base in self.my_base:
					if self.BLAST_ENABLED:
						count = 0
						for s in self.surroundings:
							c = self.g.GetCell(base[0]+s[0], base[1]+s[1])
							if c!= None:
								if c.owner != self.g.uid and c.owner != 0:
									count += 1
						if count >= 4:
							if self.status['energy'] > 40:
								print(self.g.Blast(base[0], base[1], "square"))
								self.update()
					for s in self.surroundings:
						if (base[0]+s[0], base[1]+s[1]) in self.border_cell:
							b = self.g.GetCell(base[0], base[1])
							if 1 < b.takeTime < 3.5:
								print(self.g.AttackCell(base[0], base[1], self.boost(b)))
								self.update()
								break
						c = self.g.GetCell(base[0]+s[0], base[1]+s[1])
						if c != None:
							if c.owner != self.g.uid:
								if not self.status['isTaking'] and not c.isTaking:
									if self.get_take_time(c) <= 8:
										print(self.g.AttackCell(base[0]+s[0], base[1]+s[1], self.boost(c)))
										self.update()
										break
							else:
								if not self.status['isTaking'] and not c.isTaking:
									if 1 < c.takeTime <= 3.5:
										for ss in self.surroundings:
											if (c.x+ss[0], c.y+ss[1]) in self.border_cell:
												print(self.g.AttackCell(base[0]+s[0], base[1]+s[1]))
												self.update()
												break
		
		# resource blast
		if self.BLAST_ENABLED:
			if self.my_energy:
				for energy in self.my_energy:
					count = 0
					for s in self.surroundings:
						c = self.g.GetCell(energy[0]+s[0], energy[1]+s[1])
						if c!= None:
							if c.owner != self.g.uid and c.owner != 0:
								count += 1
					if count >= 4:
						if self.status['energy'] > 40:
							print(self.g.Blast(energy[0], energy[1], "square"))
							self.update()
		
		# reinforce border
		if self.status['mode'] != 0 and self.status['mode'] != 1 and self.status['mode'] != 4\
		and len(self.border_cell) < 40:
			for cell in self.border_cell:
				c = self.g.GetCell(cell[0], cell[1])
				for d in self.directions:
					cc = self.g.GetCell(cell[0]+d[0], cell[1]+d[1])
					if cc != None:
						if cc.owner != 0 and cc.owner != self.g.uid: 
							if 1 < c.takeTime <= 3.5:
								print(self.g.AttackCell(cell[0], cell[1]))
								self.update()
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
		if self.status['isTaking']:
			return
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
			target = self.on_enemy_base
		elif tar == 'base_round':
			target = self.on_enemy_base_round
			base = self.on_enemy_base[0]
			self.gr[base[0]][base[1]].val = math.inf
		else:
			print("Error: invalid target!")
			return
		
		for cell in target:
			if cell not in self.my_cell:
				if tar != 'base':
					targets.append(self.gr[cell[0]][cell[1]])
				else:
					if self.on_enemy == 0:
						targets.append(self.gr[cell[0]][cell[1]])
					else:
						c = self.g.GetCell(cell[0], cell[1])
						if c.owner == self.on_enemy:
							targets.append(self.gr[cell[0]][cell[1]])
		
		if (tar == 'base' or tar == 'base_round') and self.on_enemy != 0:
			for cell in self.on_enemy_cell:
				c = self.g.GetCell(cell[0], cell[1])
				if c.isBuilding:
					targets = []
					targets.append(self.gr[cell[0]][cell[1]])
					break
		
		v = Vertex(-1, 0, 0)
		
		while (search_set):
			min = math.inf
			for ver in search_set:
				if ver.dist < min:
					min = ver.dist
					v = ver
			if v not in search_set:
				break
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
						
		if tar == 'base':
			if self.on_enemy == 0 or not self.on_enemy_base:
				b = self.g.GetCell(v.x, v.y)
				self.on_enemy = b.owner
				self.on_enemy_base = []
				self.on_enemy_base.append((v.x, v.y))
				self.update()
				self.get_target()
			self.on_enemy_base = []
			self.on_enemy_base.append((v.x, v.y))
		
		self.path = []
		while(v.preBest):
			self.path.append(v)
			v = v.preBest
			
	# whether boost or not
	def boost(self, cell):
		take_time = self.get_take_time(cell)
		if self.status['energy'] > 15:
			if self.status['energy'] >= 90:
				if take_time >= 1.5:
					return True
				else:
					return False
			elif self.status['energy'] >= 50:
				if self.g.energyCellNum >= 3:
					if take_time >= 3:
						return True
					else:
						return False
				elif self.g.energyCellNum >= 1:
					if take_time >= 4:
						return True
					else:
						return False
				else:
					return False
			elif self.g.energyCellNum >= 5 and take_time >= 4:
				return True
			else:
				return False
		else:
			return False
	
	# when, where and how to blast
	def blast(self):
		self.blast_mode = -1
		
		# regular blast
		
		
		
		
		return
		
	# when, where to multiattack
	def multiattack(self):
		
		return
		
	def multisort(self):
		
		
		return
	
		
						
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

	