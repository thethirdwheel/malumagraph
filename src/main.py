import cmudict
import os
import sys
import string
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import plotly.figure_factory as ff

#mapping from arpabet to roundness
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
						#syllableCounter += 1
					else:
						stresses.append(0)
					scores.append(phone2roundness[phone])
					sounds.append(phone)
				scores.append(0.5)
				stresses.append(0)
				sounds.append("")
		poem_scores.append(scores)
		poem_stresses.append(stresses)
		poem_sounds.append(sounds)
for i in poem_scores:
	if len(i) > cols:
		cols = len(i)
print(f"rows: {rows} cols: {cols}", file=sys.stderr)

justified_scores = np.zeros(shape=(rows,cols))
justified_sounds= np.empty(shape=(rows,cols), dtype="str")

for i, row in enumerate(poem_scores):
	for j, val in enumerate(row):
		justified_scores[i][j] = val
		justified_sounds[i][j] = poem_sounds[i][j]
print(justified_scores, file=sys.stderr)
print(justified_sounds, file=sys.stderr)

#fig = make_subplots(rows=1, cols=2)
#fig.add_trace(go.Contour(z=poem_scores, line_smoothing=0.85), 1, 2)
fig = ff.create_annotated_heatmap(np.flip(justified_scores,0), annotation_text=np.flip(justified_sounds,0))
img = fig.to_image(format="svg")
with os.fdopen(sys.stdout.fileno(), "wb", closefd=False) as stdout:
    stdout.write(img)
    stdout.flush()

