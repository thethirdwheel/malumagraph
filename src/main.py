import cmudict
import os
import sys
import string
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import plotly.figure_factory as ff

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


def make_cmudict(cmudict_file="cmudict.rep"):
	word2phone = {}
	with open(cmudict_file) as f:
		for l in f:
			if l[0:2] != "##":
				vals = l.strip().split("  ")
				word2phone[vals[0]] = Syllabification(vals[0], vals[1])
	return word2phone

phone2spikiness= make_phone_scores()
print(phone2spikiness,file=sys.stderr)
word2phone = make_cmudict()
punctuation_table = str.maketrans(dict.fromkeys(string.punctuation))
poem_scores = []
poem_stresses = []
poem_sounds= []
rows = 0
cols = 0
with open("corpus.txt") as f:
	for l in f:
		rows += 1
		scores = []
		stresses = []
		sounds = []
		for word in l.split(" "):
			clean_word = word.upper().strip().translate(punctuation_table)
			w = None
			if clean_word in word2phone:
				w = word2phone[clean_word]
			else:
				print(clean_word,file=sys.stderr)
			if w and w.syllables:
				for s in w.syllables:
					for p in s.phones:
						print(f"phone:{p} type:{type(p)}",file=sys.stderr)
						p.score = phone2spikiness[p.phone]
					scores.append(s.score())
					sounds.append(s)
			scores.append(None)
			sounds.append(None)
		poem_scores.append(scores)
		poem_sounds.append(sounds)

for i in poem_scores:
	if len(i) > cols:
		cols = len(i)

justified_scores = np.full(shape=(rows,cols), fill_value=None)

for i, row in enumerate(poem_scores):
	for j, val in enumerate(row):
		#Adjust scores to be negative if round, positive if spiky, and centered at 0 
		if val:
			justified_scores[i][j] = (val - 0.5)*-1.0
		else:
			justified_scores[i][j] = None
for sound in poem_sounds:
	if sound:
		print(sound,file=sys.stderr)
fig = polar_dists(justified_scores, cols)
#fig = sparklines(justified_scores, cols)
#fig = annotated_heat_map(justified_scores, justified_sounds)
#fig = contour_map(justified_scores)
img = fig.to_image(format="svg")
with os.fdopen(sys.stdout.fileno(), "wb", closefd=False) as stdout:
    stdout.write(img)
    stdout.flush()

#Joe's idea for producing sound-shape correspondence (instead of graphing "spikiness")
#Create (normal) distribution
#Tune distribution with variance proportional to spikiness and mean proportional to stress
#Draw number of points from distribution proportional to word length
#Graph in polar coordinates where r is the value drawn from the distribution and theta is position in the poem