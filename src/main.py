import cmudict
import os
import sys
import string
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import plotly.figure_factory as ff
import cairo
import math

def polar_dists(scores, cols):
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
	temp_scores = scores
	temp_scores[temp_scores == None] = 0
	temp_scores = np.vstack([temp_scores, np.zeros_like(temp_scores[0])])
	temp_scores = np.insert(temp_scores, 0, 0, axis=0)
	temp_scores = np.insert(temp_scores, 0, 0, axis=1)
	temp_scores = np.flip(temp_scores,0)
	fig = go.Figure(data = go.Contour(z=temp_scores, line_smoothing=0.85))
	return fig

def annotated_heat_map(scores, sounds):
	#Have to flip the arrays so that text is displayed in order
	temp_scores = np.flip(scores,0)
	temp_scores[temp_scores == None] = 0
	fig = ff.create_annotated_heatmap(temp_scores, annotation_text=np.flip(sounds,0))
	return fig

def sparklines(scores, cols):
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
	phone2spikiness = {}
	with open(phoneme_csv) as f:
		for l in f:
			vals = l.split(",")
			#spiky is positive, 0 is neutral, round is negative
			#phone2spikiness[vals[0]] = (float(vals[1])-0.5)
			phone2spikiness[vals[0]] = float(vals[1])
	return phone2spikiness

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
		s = 0
		for p in self.phones:
			if p and p.score:
				s += p.score
		return s*2**self.stress

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

def draw_syllable(ctx, x, y, syl):
	syllable_len = 0
	syllable_height = 30 + 30*syl.stress*0.5
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
	#ctx.stroke()	
	return syllable_len

def draw_word(ctx, x, y, word):
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
	#ctx.stroke()
	return word_len

def draw_corpus(structured_corpus):
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
		ctx.stroke()
		surface.flush()

def make_cmudict(cmudict_file="cmudict.rep"):
	word2phone = {}
	with open(cmudict_file) as f:
		for l in f:
			if l[0:2] != "##":
				vals = l.strip().split("  ")
				word2phone[vals[0]] = Syllabification(vals[0], vals[1])
	return word2phone

phone2spikiness= make_phone_scores()
#print(phone2spikiness,file=sys.stderr)
word2phone = make_cmudict()
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
		sounds = []
		structured_line = []
		for word in l.split(" "):
			clean_word = word.upper().strip().translate(punctuation_table)
			w = None
			if clean_word in word2phone:
				w = word2phone[clean_word]
			else:
				print(f"couldn't find word: {clean_word}",file=sys.stderr)
			if w and w.syllables:
				for s in w.syllables:
					for p in s.phones:
						p.score = phone2spikiness[p.phone]
						#print(f"phone:{p} type:{type(p)}",file=sys.stderr)
					scores.append(s.score())
					sounds.append(s)
				structured_line.append(w)
			scores.append(None)
			sounds.append(None)
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
#fig = polar_dists(justified_scores, cols)
#fig = sparklines(justified_scores, cols)
#fig = annotated_heat_map(justified_scores, justified_sounds)
#fig = contour_map(justified_scores)
#img = fig.to_image(format="svg")
#with os.fdopen(sys.stdout.fileno(), "wb", closefd=False) as stdout:
    #stdout.write(img)
    #stdout.flush()
draw_corpus(structured_corpus)

#Joe's idea for producing sound-shape correspondence (instead of graphing "spikiness")
#Create (normal) distribution
#Tune distribution with variance proportional to spikiness and mean proportional to stress
#Draw number of points from distribution proportional to word length
#Graph in polar coordinates where r is the value drawn from the distribution and theta is position in the corpus