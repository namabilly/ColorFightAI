# You need to import colorfight for all the APIs
import colorfight
import random

# Strategies
# 1. Go for the energy cell
# 2. Greedy expand
# 3. Select move with least neighbors
# 4. Go for the base!
# 5. Self defense

# TODO: Implement graph
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
		self.target = []
		self.modes = ["energy", "fast", "safe", "attack", "defend"]
		self.status = {
			'energy': 0,
			'energyGrowth': 0,
			'gold': 0,
			'goldGrowth': 0,
			'cellNum': 1,
			'baseNum': 1,
			'cdTime': 0,
			'isDangerous': False,
			'mode': 0
		}
		
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
			
			while True:
				# do stuff
				self.g.Refresh()
				self.update()
				print(self.status)
				self.move()
				cell = self.target[0]
				print(self.g.AttackCell(cell[0], cell[1]))
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
				
		# update neighbors & borders
		self.neighbor_cell = []
		self.border_cell = []
		for cell in self.my_cell:
			x, y = cell
			for d in self.directions:
				c = self.g.GetCell(x+d[0], y+d[1])
				if c != None:
					if c.owner != self.g.uid:
						if c not in self.neighbor_cell:
							self.neighbor_cell.append((x+d[0], y+d[1]))
						if cell not in self.border_cell:
							self.border_cell.append(cell)
		
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
		self.status['baseNum'] = self.g.baseNum
		self.status['cdTime'] = self.g.cdTime
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
			self.status['mode'] = 4
		elif self.status['energyGrowth'] < 0.3:
			self.status['mode'] = 0
		elif self.status['cellNum'] < 100:
			self.status['mode'] = 1
		elif self.status['cellNum'] < 200:
			self.status['mode'] = 2
		else:
			self.status['mode'] = 3
		
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
			self.status['mode'] = 1
			self.get_target()
		# mode 1 - fast
		# greedy expand
		# assign value to neighbor cells, choose the highest one, i.e. shorter time and better benefit
		elif self.modes[self.status['mode']] == "fast":
			neighborCell = []
			for cell in self.neighbor_cell:
				neighborCell.append(self.g.GetCell(cell[0], cell[1]))
			neighborCell.sort(key = self.get_val, reverse = True)
			for cell in neighborCell:
				if not cell.isTaking:
					self.target.append((cell.x, cell.y))
					break
			else:
				self.target.append(neighborCell[0].x, neighborCell[0].y)
		# mode 2 - safe
		# now you want to play safe
		# choose the move to minimize neighbors
		elif self.modes[self.status['mode']] == "safe":
			self.status['mode'] = 1
			self.get_target()
		# mode 3 - attack
		# get rid of other players!
		elif self.modes[self.status['mode']] == "attack":
			self.status['mode'] = 1
			self.get_target()
		# mode 4 - defend
		# not too much of a concern now
		elif self.modes[self.status['mode']] == "defend":
			self.status['mode'] = 1
			self.get_target()
		else:
			print("Error: mode not defined.")
			
	def get_val(self, cell):
		take_time = cell.takeTime
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
			
	def move(self):
		# build base - 60g, 30s
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
		for cell in self.border_cell:
			c = self.g.GetCell(cell[0], cell[1])
			if c.takeTime < 4.5:
				print(self.g.AttackCell(cell[0], cell[1]))
				self.update()
				self.g.Refresh()
		
		return
	
	
if __name__ == '__main__':
	ai = NamabillyAI()
	ai.run()

	