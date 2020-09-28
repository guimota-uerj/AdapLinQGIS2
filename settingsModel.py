import pickle
import os

class settingsModel():
	"""docstring for settingsModel"""
	def __init__(self):

		self.path = os.path.dirname(os.path.abspath(__file__)) + "/settingsInfo.dat"

	def load(self):

		try: 
			info = pickle.load(open(self.path, "rb"))	
			return info

		except:
			return False

	def save(self,info):

		pickle.dump(info, open(self.path, "wb"))