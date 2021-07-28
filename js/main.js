// main.js

const express = require("express");
const app = express();

const PORT = process.env.PORT || 8080;

app.get("/", (req, res) => {
  res.send(`
    <h1>Docker + Node</h1>
    <span>A bizarre and SO SO SO silly match made in the <b>sometimes</b> changing cloud</span>
  `);
});

app.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}...`);
});