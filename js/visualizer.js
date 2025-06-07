const fs = require('fs');

function makePhoneScores(csvFile) {
  const lines = fs.readFileSync(csvFile, 'utf8').trim().split(/\r?\n/);
  const phone2score = {};
  for (const line of lines) {
    const [ph, val] = line.split(',');
    phone2score[ph] = parseFloat(val);
  }
  return phone2score;
}

class Phone {
  constructor(phone, score) {
    this.phone = phone;
    this.score = score;
  }
}

class Syllable {
  constructor(stress, phones) {
    this.stress = parseInt(stress, 10);
    this.phones = phones;
  }
  score() {
    const vals = this.phones.map(p => p.score || 0);
    return vals.length ? vals.reduce((a,b)=>a+b,0)/vals.length : 0;
  }
}

class Syllabification {
  constructor(word, desc) {
    this.word = word;
    this.syllables = [];
    for (const part of desc.split(' - ')) {
      const pieces = part.trim().split(' ').filter(Boolean);
      let stress = 0;
      const phones = [];
      for (const p of pieces) {
        const m = p.match(/(\D+)(\d)?/);
        if (m) {
          const phone = m[1];
          if (m[2]) stress = parseInt(m[2],10);
          phones.push(new Phone(phone, null));
        }
      }
      this.syllables.push(new Syllable(stress, phones));
    }
  }
}

function makeCmudict(file) {
  const map = {};
  const lines = fs.readFileSync(file, 'utf8').split(/\r?\n/);
  for (const line of lines) {
    if (!line || line.startsWith('##')) continue;
    const idx = line.indexOf('  ');
    if (idx !== -1) {
      const word = line.slice(0, idx);
      const desc = line.slice(idx+2).trim();
      map[word] = new Syllabification(word, desc);
    }
  }
  return map;
}

function makeStructuredCorpus(corpusFile, dict, phoneScores) {
  const punct = /[!"#$%&'()*+,\-.\/\d:;<=>?@[\\\]^_`{|}~]/g;
  const lines = fs.readFileSync(corpusFile, 'utf8').trim().split(/\r?\n/);
  const structured = [];
  for (const line of lines) {
    const words = line.split(/\s+/);
    const outLine = [];
    for (const w of words) {
      const clean = w.toUpperCase().replace(punct, '');
      const syl = dict[clean];
      if (!syl) continue;
      for (const s of syl.syllables) {
        for (const p of s.phones) {
          p.score = phoneScores[p.phone] || 0;
        }
      }
      outLine.push(syl);
    }
    structured.push(outLine);
  }
  return structured;
}

function distance(x,y,x1,y1){
  return Math.sqrt((x1-x)**2+(y1-y)**2);
}

function x1y1GivenYmXbD(y,m,x,b,d){
  const x1 = (Math.sqrt(-1*b**2 - 2*b*m*x + 2*b*y + d**2*m**2 + d**2 - m**2*x**2 + 2*m*x*y - y**2) - b*m + m*y + x)/(m**2 + 1);
  const y1 = m*x1 + b;
  const altx1 = x + (x - x1);
  const alty1 = m*altx1 + b;
  if (distance(x1,y1,0,0) < distance(altx1,alty1,0,0)) {
    return [altx1, alty1];
  }
  return [x1, y1];
}

function mbFromPoints(x1,y1,x2,y2){
  if (x2 === x1) return [null,null];
  const m = (y2 - y1)/(x2 - x1);
  const b = y1 - m*x1;
  return [m,b];
}

function drawPolycloud(sides, roundness){
  const unitAngle = 2*Math.PI / sides;
  const x0 = 0, y0 = 1;
  let x = x0, y = y0;
  let path = `M ${x} ${y} `;
  for (let i=0;i<sides;i++){
    const curAngle = unitAngle*(i+1);
    const curX = x0*Math.cos(curAngle) + y0*Math.sin(curAngle);
    const curY = x0*Math.sin(curAngle) + y0*Math.cos(curAngle);
    if ((curX - x) !== 0){
      const m = (curY - y)/(curX - x);
      const perpM = -1/m;
      const b1 = y - perpM*x;
      const b2 = curY - perpM*curX;
      const [x1,y1] = x1y1GivenYmXbD(y, perpM, x, b1, distance(x,y,curX,curY));
      const [x2,y2] = x1y1GivenYmXbD(curY, perpM, curX, b2, distance(x,y,curX,curY));
      const [guideM, guideB] = mbFromPoints(x1,y1,x2,y2);
      const cp1x = x1*roundness + x2*(1-roundness);
      const cp1y = guideM !== null ? guideM*cp1x + guideB : y1*roundness + y2*(1-roundness);
      const cp2x = x1*(1-roundness) + x2*roundness;
      const cp2y = guideM !== null ? guideM*cp2x + guideB : y1*(1-roundness) + y2*roundness;
      path += `C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${curX} ${curY} `;
      x = curX; y = curY;
    }
  }
  return `<path d="${path}" fill="none" stroke="black"/>`;
}

function drawPolycloudSyllable(syl){
  const l = 5 + 2*syl.phones.length;
  const h = 5 + 5*syl.stress;
  const poly = drawPolycloud(3*syl.phones.length, syl.score());
  return [`<g transform="scale(${l},${h})">${poly}</g>`, l*3];
}

function drawWord(word){
  const syllableBuffer = 10;
  let wordLen = syllableBuffer;
  let svg = '';
  for (const syl of word.syllables){
    const [sylSvg, sylLen] = drawPolycloudSyllable(syl);
    svg += `<g transform="translate(${wordLen},15)">${sylSvg}</g>`;
    wordLen += sylLen + syllableBuffer;
  }
  wordLen -= syllableBuffer;
  return [svg, wordLen];
}

function drawCorpus(structured){
  const width = 612, height = 792;
  let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}">`;
  let xpos = 10, ypos = 20;
  for (const line of structured){
    for (const w of line){
      const [wordSvg, len] = drawWord(w);
      svg += `<g transform="translate(${xpos},${ypos})">${wordSvg}</g>`;
      xpos += len + 20;
    }
    ypos += 60;
    xpos = 10;
  }
  svg += '</svg>';
  return svg;
}

function main(){
  const phoneScores = makePhoneScores('phoneme_roundness.csv');
  const dict = makeCmudict('cmudict.rep');
  const structured = makeStructuredCorpus('corpus.txt', dict, phoneScores);
  const svg = drawCorpus(structured);
  fs.writeFileSync('output.svg', svg);
}

main();
