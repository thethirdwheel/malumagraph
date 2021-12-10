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

def polar_dists(scores, cols):
	'''Make a pretty plot of scores in polar coordinates; it's not very useful honestly'''
	temp_scores = scores
	temp_scores[temp_scores == None] = 0
	num_lines = len(temp_scores)
	fig = make_subplots(num_lines, cols)
	for i, line in enumerate(temp_scores, start=1):
		for j, score in enumerate(line):
			print(f"score:{score}", file=sys.stderr)
			fig.add_trace(go.Scatterpolar(r=np.random.normal(scale=score,size=24), theta=list(range(0,345,15)), mode='lines'))
	return fig

def contour_map(scores):
	'''Make a simple contour-map representation of scores'''
	temp_scores = scores
	temp_scores[temp_scores == None] = 0
	temp_scores = np.vstack([temp_scores, np.zeros_like(temp_scores[0])])
	temp_scores = np.insert(temp_scores, 0, 0, axis=0)
	temp_scores = np.insert(temp_scores, 0, 0, axis=1)
	temp_scores = np.flip(temp_scores,0)
	fig = go.Figure(data = go.Contour(z=temp_scores, line_smoothing=0.85))
	return fig

def annotated_heat_map(scores, sounds):
	'''make an annotated heatmap of the scores; this is a nice way of making sure you aren't crazy when changing the scoring function'''
	#Have to flip the arrays so that text is displayed in order
	temp_scores = np.flip(scores,0)
	temp_scores[temp_scores == None] = 0
	fig = ff.create_annotated_heatmap(temp_scores, annotation_text=np.flip(sounds,0))
	return fig

def sparklines(scores, cols):
	'''generate sparklines for the given scores; this is a nice way of making sure you aren't crazy when changing the scoring function'''
	temp_scores = scores
	temp_scores[temp_scores == None] = 0
	num_lines = len(temp_scores)
	fig = make_subplots(num_lines, 1)
	for index, line in enumerate(temp_scores, start=1):
		fig.add_trace(go.Scatter(y=line, x=list(range(0,cols)), mode='lines'), index, 1)
	fig.update_xaxes(visible=False, fixedrange=True)
	fig.update_yaxes(visible=True)
	fig.update_layout(annotations=[], overwrite=True)
	fig.update_layout(
		showlegend=False,
		plot_bgcolor="white",
		margin=dict(t=10,l=10,b=10,r=10)
		)
	return fig

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
	syllable_height = 30 + 30*syl.stress*0.25
	my_x = x
	my_y = y
	r = 5.0
	ctx.move_to(my_x+r,my_y)
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
	return syllable_len

def draw_word(ctx, x, y, word):
	'''let's make boxes with syllables inside them'''
	syllable_buffer = 10
	word_height = 20
	syllable_height = 30
	#print(f"word: {word.word} syllables: {word.syllables}",file=sys.stderr)
	word_len = syllable_buffer 
	for i, syl in enumerate(word.syllables):
		rectangle_y = y - (word_height/4)
		syllable_len = draw_syllable(ctx,x+word_len,rectangle_y+15,syl)
		word_len = word_len + syllable_len + syllable_buffer
	word_len = word_len - (syllable_buffer)
	ctx.rectangle(x, y, word_len, word_height)
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
				word_len = draw_word(ctx, xpos, ypos, w)
				xpos = xpos + word_len + 20
			ypos = ypos + 60
			xpos = 10
		ctx.set_source_rgb(0.3, 0.2, 0.5)  # Solid color
		ctx.stroke()
		surface.flush()

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


if not os.path.exists("cmudict.db"):
	phone2spikiness= make_phone_scores()
	#print(phone2spikiness,file=sys.stderr)
	word2phone = make_cmudict()
	cmudict_to_sqlite(word2phone, phone2spikiness)
	#There's something wrong with this that is leading to a "sqlite3.DatabaseError: file is not a database"
	#with open("cmudict.db", 'rb') as fin:
	#	sys.stdout.buffer.write(b"%s" % fin.read())
	#quit()
else:
	print("using pre-existing sqlite database", file=sys.stderr)
	phone2spikiness= make_phone_scores()
	#print(phone2spikiness,file=sys.stderr)
	word2phone = make_cmudict()
	cmudict_to_sqlite(word2phone, phone2spikiness)


#All of the below is very ugly, maintaining a lot of global state, poor encapsulation, business logic+I/O &c, will fix later
con = sqlite3.connect("cmudict.db")
cur = con.cursor()
punctuation_table = str.maketrans(dict.fromkeys(string.punctuation))
corpus_scores = []
corpus_stresses = []
structured_corpus = []
rows = 0
cols = 0
with open("corpus.txt") as f:
	for l in f:
		rows += 1
		scores = []
		stresses = []
		structured_line = []
		for word in l.split(" "):
			clean_word = word.upper().strip().translate(punctuation_table)
			w = None
			try:
				#the funky trailing , after clean_word is to help python realize that this is a sequence (necessary for the qmark syntax)
				cur.execute("SELECT syllabification FROM cmudict WHERE word=? LIMIT 1", (clean_word,))
				w = cur.fetchone()
				if w:
					#do some json parsing to get the goods
					w_json=json.loads(w[0])
					w_syllabification = Syllabification.from_json(clean_word, w[0])
					for s in w_json:
						phone_scores = []
						for p in s:
							if type(p) is dict:
								items = list(p.items())
								phone_scores.append(items[0][1])
						scores.append(score_syllable(s[0],phone_scores))
					structured_line.append(w_syllabification)
				else:
					print(f"couldn't find word: {clean_word}",file=sys.stderr)	
			except sqlite3.ProgrammingError:
				print(clean_word,file=sys.stderr)
				raise
			scores.append(None)
		corpus_scores.append(scores)
		structured_corpus.append(structured_line)

for i in corpus_scores:
	if len(i) > cols:
		cols = len(i)

justified_scores = np.full(shape=(rows,cols), fill_value=None)

for i, row in enumerate(corpus_scores):
	for j, val in enumerate(row):
		#Adjust scores to be negative if round, positive if spiky, and centered at 0 
		if val:
			justified_scores[i][j] = val #(val - 0.5)*-1.0
		else:
			justified_scores[i][j] = None
draw_corpus(structured_corpus)

#Joe's idea for producing sound-shape correspondence (instead of graphing "spikiness")
#Create (normal) distribution
#Tune distribution with variance proportional to spikiness and mean proportional to stress
#Draw number of points from distribution proportional to word length
#Graph in polar coordinates where r is the value drawn from the distribution and theta is position in the corpus