import cmudict
import os
import sys
import string
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import plotly.figure_factory as ff

#mapping from arpabet to roundness (should move to a file)
phone2roundness = {
	'AA' : 0.70, #Non-Front
	'AE' : 0.49, #Front
	'AH' : 0.70, #Non-Front
	'AO' : 0.70, #Non-Front
	'AW' : 0.70, #Non-Front
	'AX' : 0.49, #Front
	'AXR' : 0.70, #Non-Front
	'AY' : 0.49, #Front
	'EH' : 0.49, #Front
	'ER' : 0.49, #Front
	'EY' : 0.70, #Non-Front
	'IH' :  0.49, #Front
	'IX' :  0.49, #Front
	'IY' :  0.49, #Front
	'OW' :  0.70, #Non-Front
	'OY' :  0.70, #Non-Front
	'UH' :  0.70, #Non-Front
	'UW' :  0.70, #Non-Front
	'UX' :  0.70, #Non-Front
	'B' : 0.69, #voiced labial
	'CH' : 0.11, #voiceless alveolar
	'D' : 0.64, #voiced alveolar
	'DH' : 0.4, #voiced dental 
	'DX' : 0.64, #voiced alveolar
	'EL' : 0.64, #voiced alveolar
	'EM' : 0.69, #voiced labial
	'EN' : 0.64, #voiced alveolar
	'F' : 0.75, #voiceless labial
	'G' : 0.72, #voiced velar
	'HH' : 0.3, #voiceless glottal (we're pretending it's velar)
	'H' : 0.3, #voiceless glottal (we're pretending it's velar)
	'JH' : 0.64, #voiced alveolar
	'K' : 0.3, #voiceless velar
	'L' : 0.64, #voiced alveolar
	'M' : 0.69, #voiced labial
	'N' : 0.64, #voiced alveolar
	'NX' : 0.72, #voiced velar
	'NG' : 0.72, #voiced velar
	'NX' : 0.64, #voiced alveolar
	'P' : 0.75, #voiceless labial
	'Q' : 0.3, #voiceless glottal (this is a weird ridiculous one; we're pretending velar)
	'R' : 0.64, #voiced alveolar
	'S' : 0.11, #voiceless alveolar
	'SH' : 0.3, #voiceless postalveolar (we're pretending it's velar)
	'T' : 0.11, #voiceless alveolar
	'TH' : 0.64, #voiceless dental (tricky one to properly assign, placeholder)
	'V' : 0.69, #voiced labial
	'W' : 0.72, #voiced velar
	'WH' : 0.3, #voiceless velar
	'Y' : 0.72, #voiced velar
	'Z' : 0.64, #voiced alveolar
	'ZH' : 0.72 #voiced velar
}
word2phone = cmudict.dict()

def contour_map(scores):
	temp_scores = scores
	temp_scores[temp_scores == None] = 0
	temp_scores = np.vstack([temp_scores, np.zeros_like(temp_scores[0])])
	temp_scores = np.insert(temp_scores, 0, 0, axis=0)
	temp_scores = np.insert(temp_scores, 0, 0, axis=1)
	fig = go.Figure(data = go.Contour(z=temp_scores, line_smoothing=0.85))
	return fig

def annotated_heat_map(scores, sounds):
	#Have to flip the arrays so that text is displayed in order
	temp_scores = np.flip(scores,0)
	temp_scores[temp_scores == None] = 0
	fig = ff.create_annotated_heatmap(temp_scores, annotation_text=np.flip(sounds,0))
	return fig

def sparklines(scores, cols):
	num_lines = len(scores)
	fig = make_subplots(num_lines, 1)
	for index, line in enumerate(scores, start=1):
		fig.add_trace(go.Scatter(y=line, x=list(range(0,cols)), mode='lines'), index, 1)
	fig.update_xaxes(visible=False, fixedrange=True)
	fig.update_yaxes(visible=False, fixedrange=True)
	fig.update_layout(annotations=[], overwrite=True)
	fig.update_layout(
		showlegend=False,
		plot_bgcolor="white",
		margin=dict(t=10,l=10,b=10,r=10)
		)
	return fig

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
			phones = word2phone[word.lower().strip().translate(punctuation_table)]
			if phones and phones[0]:
				for phone in phones[0]:
					if phone[-1].isdigit():
						stresses.append(phone[-1])
						phone = phone[0:-1]
					else:
						stresses.append(0)
					scores.append(phone2roundness[phone])
					sounds.append(phone)
				scores.append(None)
				stresses.append(None)
				sounds.append(None)
		poem_scores.append(scores)
		poem_stresses.append(stresses)
		poem_sounds.append(sounds)
for i in poem_scores:
	if len(i) > cols:
		cols = len(i)
print(f"rows: {rows} cols: {cols}", file=sys.stderr)

justified_scores = np.full(shape=(rows,cols), fill_value=None)
justified_sounds= np.empty(shape=(rows,cols), dtype="str")

for i, row in enumerate(poem_scores):
	for j, val in enumerate(row):
		#Adjust scores to be negative if spiky, positive if round
		if val:
			justified_scores[i][j] = val - 0.5
		else:
			justified_scores[i][j] = None
		justified_sounds[i][j] = poem_sounds[i][j]
print(justified_scores, file=sys.stderr)
print(justified_sounds, file=sys.stderr)

fig = sparklines(justified_scores, cols)
#fig = annotated_heat_map(justified_scores, justified_sounds)
#fig = contour_map(justified_scores)
img = fig.to_image(format="svg")
with os.fdopen(sys.stdout.fileno(), "wb", closefd=False) as stdout:
    stdout.write(img)
    stdout.flush()
