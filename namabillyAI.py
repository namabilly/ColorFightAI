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
				self.update()
				# print(self.status)
				cell = self.target[0]
				print(self.g.AttackCell(cell[0], cell[1]))
				self.g.Refresh()
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
		
		self.get_target()
	
	def get_target(self):
		self.target = []
		# mode 0 - energy
		
		neighborCell = []
		for cell in self.neighbor_cell:
			neighborCell.append(self.g.GetCell(cell[0], cell[1]))
		neighborCell.sort(key = self.get_take_time)
		for cell in neighborCell:
			if not cell.isTaking:
				self.target.append((cell.x, cell.y))
				break
		else:
			self.target.append(neighborCell[0].x, neighborCell[0].y)
			
	def get_take_time(self, cell):
		take_time = cell.takeTime
		neighborNum = 0;
		for d in self.directions:
			c = self.g.GetCell(cell.x+d[0], cell.y+d[1])
			if c != None:
				if c.owner == self.g.uid:
					neighborNum += 1
		return (take_time * min(1, 1 - 0.25*(neighborNum - 1))) / (1 + self.status['energy']/200.0)
			
	def move(self):
		# build base; cost 60g, 30s
		return
	
	
if __name__ == '__main__':
	ai = NamabillyAI()
	ai.run()

	