import cmudict
import os
import sys
import string
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import plotly.figure_factory as ff
import cairo
import sqlite3
import math
import json
import argparse

def make_phone_scores(phoneme_csv="phoneme_roundness.csv"):
	'''take a phonemee_roundness csv and turn it into some (pretty arbitrary) scores'''
	phone2spikiness = {}
	with open(phoneme_csv) as f:
		for l in f:
			vals = l.split(",")
			#spiky is positive, 0 is neutral, round is negative
			#phone2spikiness[vals[0]] = (float(vals[1])-0.5)
			phone2spikiness[vals[0]] = float(vals[1])
	return phone2spikiness

def score_syllable(stress, phone_scores):
	'''take stress and list of phone roundness scores and return a total score'''
	s = sum(phone_scores)
	return s*2**stress

class Phone:
	def __init__(self, phone, score):
		self.phone = phone
		self.score = score

	def __repr__(self):
		return f"{self.phone} ({self.score})"

class Syllable:
	def __init__(self, stress, phones):
		self.stress = int(stress)
		self.phones = phones

	def __repr__(self):
		return f"stress: {self.stress} phones: {self.phones}"

	def __str__(self):
		return f"stress: {self.stress} phones: {self.phones}"

#scoring function for syllables (quite arbitrary at the moment)
	def score(self):
		phone_scores = []
		for p in self.phones:
			if p and p.score:
				phone_scores.append(p.score)
		return score_syllable(self.stress,phone_scores)

class Syllabification:
	def __init__(self, word, description):
		self.word = word
		syllables = description.split(" - ")
		self.syllables = []
		for s in syllables:
			stress = 0
			phones = []
			phone_string = s.split(" ")
			for i,p in enumerate(phone_string):
				if p[-1].isdigit():
					stress = p[-1]
					phones.append(Phone(p[:-1],None))
				else:
					phones.append(Phone(p, None))
			self.syllables.append(Syllable(stress,phones))

	def __repr__(self):
		return f"word: {self.word}, syllables: {self.syllables}"

	def __str__(self):
		return f"word: {self.word}, syllables: {self.syllables}"

	def to_json(self, phone_scores):
		'''example_syllabification = [[1, [{"AE": 0.18}, {"T":0.87}]], [0, [{"L":0.5}, {"AH":0.53}, {"S":0.87}]]]'''
		syllabification = []
		for s in self.syllables:
			syllable = [s.stress]
			for p in s.phones:
				syllable.append({p.phone: phone_scores[p.phone]})
			syllabification.append(syllable)
		return json.dumps(syllabification, separators=(',', ':'))

	def from_json(word, word_json):
		w_obj = json.loads(word_json)
		#AH0 M is just a placeholder... I know this is horribly ugly but I'm just trying to get something working
		w = Syllabification(word, "AH0 M")
		syllables = []
		for syllable in w_obj:
			stress = syllable[0]
			phones = []
			for p in syllable[1:]:
				items = list(p.items())
				phones.append(Phone(items[0][0],items[0][1]))
			syllables.append(Syllable(stress,phones))
		w.syllables = syllables
		return w


def draw_syllable(ctx, x, y, syl):
	'''love a rectangle with a wiggle in it'''
	syllable_len = 0
	syllable_height = 30
	my_x = x
	my_y = y
	r = 5.0
	ctx.save()
	ctx.move_to(my_x+r,my_y)
	ctx.scale(1.,1. + 1.*syl.stress*0.25)
	for i,p in enumerate(syl.phones):
		if (i % 2 == 0):
			if (p.score > 0.5):
				ctx.move_to(my_x+r,my_y)
				ctx.arc(my_x,my_y,r,0,math.pi)
			else:
				ctx.move_to(my_x-r,my_y)
				ctx.rel_line_to(r,r)
				ctx.rel_line_to(r,-1*r)

		else:
			if (p.score > 0.5):	
				ctx.move_to(my_x+r,my_y)
				ctx.arc_negative(my_x,my_y,r,0,-math.pi)
			else:
				ctx.move_to(my_x-r,my_y)
				ctx.rel_line_to(r,-1*r)
				ctx.rel_line_to(r,r)
		my_x = my_x + 2*r
		syllable_len = syllable_len + 2*r
	ctx.rectangle(x-r, y-(syllable_height/2), syllable_len, syllable_height)
	ctx.restore()
	return syllable_len

def draw_word(ctx, x, y, word):
	'''let's make boxes with syllables inside them'''
	syllable_buffer = 10
	word_height = 20
	word_len = syllable_buffer
	for i, syl in enumerate(word.syllables):
		rectangle_y = y - (word_height/4)
		ctx.save()
		ctx.translate(x+word_len,rectangle_y+15)
		syllable_len = draw_syllable(ctx,0,0,syl)
		ctx.restore()
		word_len = word_len + syllable_len + syllable_buffer
	word_len = word_len - (syllable_buffer)
	ctx.save()
	ctx.rectangle(x, y, word_len, word_height)
	ctx.restore()
	return word_len

def draw_corpus(structured_corpus):
	'''draw a whole corpus line by line'''
	WIDTH, HEIGHT = 612, 792
	with cairo.SVGSurface(os.fdopen(sys.stdout.fileno(), "wb", closefd=False), WIDTH, HEIGHT) as surface:
		ctx = cairo.Context(surface)
		xpos = 10
		ypos = 20 
		for l in structured_corpus:
			for w in l:
				ctx.save()
				ctx.translate(xpos,ypos)
				word_len = draw_word(ctx, 0, 0, w)
				ctx.restore()
				xpos = xpos + word_len + 20
			ypos = ypos + 60
			xpos = 10
		ctx.set_source_rgb(0.3, 0.2, 0.5)  # Solid color
		ctx.stroke()
		surface.flush()

def draw_polygon(ctx, sides):
	'''draw unit polygon with given number of sides'''
	unit_angle = 2*math.pi / sides
	x = 1
	y = 0
	#Add points at the end of the line from the center to the start, rotated by the unit angle * i
	ctx.move_to(x,y)
	for i in range(sides+1): #+1 because we want to get back to the start
		cur_x = x*math.cos(unit_angle*i) - y*math.sin(unit_angle*i)
		cur_y = x*math.sin(unit_angle*i) + y*math.cos(unit_angle*i)
		ctx.line_to(cur_x,cur_y)

#if x,y is the original point and a is the new x coordinate and the new y coordinate is ma + b, d is the desired distance from the first coordinate
#a = (sqrt(-b^2 - 2 b m x + 2 b y + d^2 m^2 + d^2 - m^2 x^2 + 2 m x y - y^2) - b m + m y + x)/(m^2 + 1)
#we also want the additional constraint that x1,y1 is always further away from the origin than x,y (so that the bulges go outwards)
def x1y1_given_ymxbd(y,m,x,b,d):
	x1 = (math.sqrt(-1*b**2 - 2*b*m*x + 2*b*y + d**2*m**2 + d**2-m**2*x**2+2*m*x*y-y**2) - b*m+m*y+x)/(m**2+1)
	y1 = m*x1+b
	#if x-x1 is positive, the alternate x1 will be greater than x, if x-x1 is negative, the alternate x1 will be less than x (i.e. it swaps the relationship between x and x1)
	alternate_x1 = x + (x-x1)
	alternate_y1 = m*alternate_x1 + b
	#We want whichever point is further from the origin (e.g. outside the shape)
	if distance(x1,y1,0,0) < distance(alternate_x1,alternate_y1,0,0):
		print(f"FLIPPING DIRECTION OF LINE: {x1},{y1} closer to 0,0 than {alternate_x1},{alternate_y1}", file=sys.stderr)
		return alternate_x1,alternate_y1
	return x1,y1

def distance(x,y,x1,y1):
	return math.sqrt((x1-x)**2+(y1-y)**2)

#calculate slope and y intercept for line passing through x1,y1 and x2,y2
def mb_from_points(x1,y1,x2,y2):
	m = (y2-y1)/(x2-x1)
	b = y1 - m*x1
	return m,b

def draw_polycloud(ctx, sides, roundness):
	'''draw unit polycloud with given number of sides (polygon with line-length bumps)'''
	unit_angle = 2*math.pi / sides
	x0 = 0
	y0 = 1
	x = x0
	y = y0
	ctx.move_to(x,y)
	for i in range(sides):
		cur_angle = unit_angle*(i+1)
		cur_x = x0*math.cos(cur_angle) + y0*math.sin(cur_angle)
		cur_y = x0*math.sin(cur_angle) + y0*math.cos(cur_angle)
	
		#why do we have this if statement? To stop ourselves from dividing by 0, only bad news is I don't know what to do instead :(
		if (cur_x-x) != 0:
			m = (cur_y-y)/(cur_x-x)
			perpendicular_m = -1/m
			b1 = y - perpendicular_m*x
			b2 = cur_y - perpendicular_m*cur_x
			x1,y1 = x1y1_given_ymxbd(y,perpendicular_m,x,b1,distance(x,y,cur_x,cur_y))
			x2,y2 = x1y1_given_ymxbd(cur_y,perpendicular_m,cur_x,b2,distance(x,y,cur_x,cur_y))
			print(f"perpendicular_m: {perpendicular_m} cur_angle: {cur_angle/math.pi}, sin: {math.sin(cur_angle)} cos: {math.cos(cur_angle)}", file=sys.stderr)
		else:
			print(f"Didn't update x1,y1,x2,y2", file=sys.stderr)
		print(f"i: {i} end1: ({x},{y}), pt1: ({x1},{y1}), pt2: ({x2},{y2}), end2: ({cur_x}, {cur_y}) dist: {distance(cur_x,cur_y,0,0)}", file=sys.stderr)
		#I think by shifting along the line x1,y1->x2,y2 we can maybe be smoothly parameterized?
		guideline_slope, guideline_intercept = mb_from_points(x1,y1,x2,y2)
		control_point_1_x = x1*roundness + x2*(1-roundness) #in theory if roundness is 1.0, control_point_1 will be at x1,y1, if it is 0 it will be at x2,y2
		control_point_1_y = guideline_slope*control_point_1_x + guideline_intercept
		control_point_2_x = x1*(1-roundness) + x2*roundness
		control_point_2_y = guideline_slope*control_point_2_x + guideline_intercept
		ctx.curve_to(control_point_1_x,control_point_1_y,control_point_2_x,control_point_2_y,cur_x,cur_y)
		x = cur_x
		y = cur_y

def make_cmudict(cmudict_file="cmudict.rep"):
	'''build an in-memory representation of the cmu pronouncing dictionary: it maps words to a string representing the phonetic syllables with stress information'''
	word2phone = {}
	with open(cmudict_file) as f:
		for l in f:
			if l[0:2] != "##":
				vals = l.strip().split("  ")
				word2phone[vals[0]] = Syllabification(vals[0], vals[1])
	return word2phone

def cmudict_to_sqlite(cmudict, phone_scores, sqlite_file="cmudict.db"):
	'''
	Okay, the actual schema is (logically) like this:

	words: (word, ordinal, stress, syllable) #maps many words to many syllables, with order and stress of syllable wrt word encoded
	syllables: (syllable, ordinal, phone) #maps many syllables to many phones, with order of phones encoded
	phones: (phone, spikiness) #maps each phone to a scalar value indicating how spikey it sounds

	Obviously, having to store the order of things that you reference in many-to-many lookup tables is appalling and fills me with dread.
	Therefore, in an appalling, dread-inducing turn, I have chosen to make this a table mapping words to json blobs.
	Here's the json blob: [{syllable: [stress, [{phone:score},{phone:score},...]]},...]
	at_example_syllable = {"AE1 T": [1, ["AE", "T"]] }
	atlas_example_syllabification = [{"AE1 T": [1, [{"AE": 0.18}, {"T":0.87}]] }, {"L AH0 S": [0, [{"L":0.5}, {"AH":0.53}, {"S":0.87}]] }]
	'''
	con = sqlite3.connect(sqlite_file)
	cur = con.cursor()
	cur.execute("create table cmudict (word, syllabification)")
	for word,syllabification in cmudict.items():
		try:
			#cur.execute("insert into cmudict values ('%s','%s')" % (word, syllabification.to_json(phone_scores))) #(word, syllabification.to_json(phone_scores)))
			cur.execute("insert into cmudict values (?,?)" , (word, syllabification.to_json(phone_scores)))
		except sqlite3.OperationalError:
			print("word: '%s'\nsyllabification: '%s'" % (word, syllabification.to_json(phone_scores)),file=sys.stderr)
			raise
	con.commit()
	con.close()

def build_sqlite_cmudict(phoneme_roundness_path, raw_path, db_path):
	phone2spikiness = make_phone_scores(phoneme_roundness_path)
	#print(phone2spikiness,file=sys.stderr)
	word2phone = make_cmudict(raw_path)
	cmudict_to_sqlite(word2phone, phone2spikiness, db_path)

def sketchbook():
	WIDTH, HEIGHT = 612, 792
	with cairo.SVGSurface(os.fdopen(sys.stdout.fileno(), "wb", closefd=False), WIDTH, HEIGHT) as surface:
		ctx = cairo.Context(surface)

		ctx.save()
		ctx.translate(40,40)
		ctx.scale(20,20)
		draw_polycloud(ctx, 4, 1)
		draw_polycloud(ctx, 4, 0.5)
		draw_polycloud(ctx, 4, 0)
		ctx.restore()

		ctx.save()
		ctx.translate(160,40)
		ctx.scale(40,20)
		draw_polycloud(ctx, 6, 1)
		ctx.restore()

		ctx.stroke()
		surface.flush()

def make_structured_corpus(corpus, cmudictdb):
	#All of the below is very ugly, maintaining a lot of global state, poor encapsulation, business logic+I/O &c, will fix later
	con = sqlite3.connect(args.cmudictdb)
	cur = con.cursor()
	punctuation_table = str.maketrans(dict.fromkeys(string.punctuation))
	#The structured corpus is an array of structured_lines
	#Each structured line is an array of Syllabifications of the words in the coinciding line in the original corpus
	structured_corpus = []
	with open(args.corpus) as f:
		for l in f:
			structured_line = []
			for word in l.split(" "):
				clean_word = word.upper().strip().translate(punctuation_table)
				w = None
				try:
					#the funky trailing ',' after clean_word is to help python realize that this is a sequence (necessary for the qmark syntax)
					cur.execute("SELECT syllabification FROM cmudict WHERE word=? LIMIT 1", (clean_word,))
					w = cur.fetchone()
					if w:
						w_syllabification = Syllabification.from_json(clean_word, w[0])
						structured_line.append(w_syllabification)
					else:
						print(f"couldn't find word: {clean_word}",file=sys.stderr)	
				except sqlite3.ProgrammingError:
					print(clean_word,file=sys.stderr)
					raise
			structured_corpus.append(structured_line)
	con.close()
	return structured_corpus

def main(args):
	if not os.path.exists(args.cmudictdb):
		build_sqlite_cmudict(args.phonemecsv,args.cmudictraw,args.cmudictdb)
	else:
		print("using pre-existing sqlite database", file=sys.stderr)

	if (args.sketchbook):
		sketchbook()
	else:
		structured_corpus = make_structured_corpus(args.corpus, args.cmudictdb)
		draw_corpus(structured_corpus)

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Transform a corpus of English text into a non-representative visualization preserving the sense of its sounds through sound-shape correspondence")
	parser.add_argument('--corpus', default="corpus.txt", help="The corpus to be processed")
	parser.add_argument('--cmudictdb', default="cmudict.db", help="The cmu pronouncing dictionary sqlite database to use")
	parser.add_argument('--cumdictraw', default="cmudict.rep", help="The raw cmudict file to use (.rep expected); only necessary if no cmudictdb given")
	parser.add_argument('--phonemecsv', default="phoneme_roundess.csv", help="The path to the .csv file containing phoneme roundness scores")
	parser.add_argument('--sketchbook', action='store_true')
	args = parser.parse_args()
	main(args)
#Joe's idea for producing sound-shape correspondence (instead of graphing "spikiness")
#Create (normal) distribution
#Tune distribution with variance proportional to spikiness and mean proportional to stress
#Draw number of points from distribution proportional to word length
#Graph in polar coordinates where r is the value drawn from the distribution and theta is position in the corpus