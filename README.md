# malumagraph
Generate language visualizations based on the bouba-kiki effect.

## Effect sizes
We use the correlations provided [here](https://www.nature.com/articles/srep26681/tables/1) to determine the effect of a phoneme on a base wave (by default, a flat line).

## Phoneme detection

We use [t2p](http://www.cs.cmu.edu/afs/cs.cmu.edu/user/lenzo/html/areas/t2p/) to parse our input into phonemes in order to calculate the curve shape. WSJ [built something](http://graphics.wsj.com/hamilton-methodology/) to visualize rhyme schemes that I'm interested in leveraging/integrating.

## Types of effect

The nature paper referred to in Effect Sizes investigates 3 kinds of manipulation, which will be used by this program: amplitude, frequency, and spikiness.  We use [this crazy shit](http://audition.ens.fr/P2web/eval2010/DP_Mesgarani2008.pdf) to figure out the contribution of each phoneme and multiply by coefficients to determine the curve shape.
