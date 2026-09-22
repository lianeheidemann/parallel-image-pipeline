async function loadBenchmark() {
  try {
    const res = await fetch("data/benchmark.csv", { cache: "no-store" });
    if (res.ok) return { rows: parseCsv(await res.text()), isSample: false };
  } catch (_) {}
  const res = await fetch("data/benchmark.sample.csv", { cache: "no-store" });
  return { rows: parseCsv(await res.text()), isSample: true };
}

function parseCsv(text) {
  const [header, ...lines] = text.trim().split("\n");
  const cols = header.split(",");
  return lines.map((line) => {
    const values = line.split(",");
    const row = {};
    cols.forEach((c, i) => (row[c] = Number(values[i])));
    return row;
  });
}

function renderChart(svg, rows) {
  const width = 640;
  const height = 260;
  const padL = 40;
  const padB = 30;
  const padT = 10;
  const padR = 10;

  const maxSpeedup = Math.max(...rows.map((r) => Math.max(r.speedup, r.speedup_amdahl_previsto))) * 1.15;
  const groupWidth = (width - padL - padR) / rows.length;
  const barWidth = groupWidth * 0.28;

  const scaleY = (v) => height - padB - (v / maxSpeedup) * (height - padT - padB);

  let svgContent = "";

  for (let g = 1; g <= 4; g++) {
    const y = scaleY((maxSpeedup / 4) * g);
    svgContent += `<line x1="${padL}" y1="${y}" x2="${width - padR}" y2="${y}" stroke="var(--border)" stroke-width="1" />`;
    svgContent += `<text x="${padL - 8}" y="${y + 4}" font-size="10" fill="var(--text-muted)" text-anchor="end">${((maxSpeedup / 4) * g).toFixed(1)}x</text>`;
  }

  rows.forEach((row, i) => {
    const groupX = padL + i * groupWidth;
    const obsX = groupX + groupWidth / 2 - barWidth - 3;
    const amdX = groupX + groupWidth / 2 + 3;

    const obsY = scaleY(row.speedup);
    const amdY = scaleY(row.speedup_amdahl_previsto);

    svgContent += `<rect x="${obsX}" y="${obsY}" width="${barWidth}" height="${height - padB - obsY}" rx="3" fill="var(--accent)" />`;
    svgContent += `<rect x="${amdX}" y="${amdY}" width="${barWidth}" height="${height - padB - amdY}" rx="3" fill="var(--amdahl)" />`;
    svgContent += `<text x="${groupX + groupWidth / 2}" y="${height - padB + 18}" font-size="12" fill="var(--text-muted)" text-anchor="middle">${row.processos}p</text>`;
  });

  svgContent += `<line x1="${padL}" y1="${height - padB}" x2="${width - padR}" y2="${height - padB}" stroke="var(--border)" stroke-width="1" />`;

  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.innerHTML = svgContent;
}

function renderTable(el, rows) {
  el.innerHTML = `
    <thead>
      <tr>
        <th>Processos</th>
        <th class="num">Tempo (s)</th>
        <th class="num">Speedup</th>
        <th class="num">Amdahl previsto</th>
      </tr>
    </thead>
    <tbody>
      ${rows
        .map(
          (r) => `<tr>
            <td>${r.processos}</td>
            <td class="num">${r.tempo_s.toFixed(2)}</td>
            <td class="num">${r.speedup.toFixed(3)}</td>
            <td class="num">${r.speedup_amdahl_previsto.toFixed(3)}</td>
          </tr>`
        )
        .join("")}
    </tbody>
  `;
}

(async function init() {
  const { rows, isSample } = await loadBenchmark();
  renderChart(document.getElementById("chart"), rows);
  renderTable(document.getElementById("table"), rows);
  if (isSample) {
    document.getElementById("data-note").textContent =
      "Dados de exemplo. Rode src/benchmark.py e copie results/benchmark.csv para docs/data/benchmark.csv para ver os resultados reais.";
  } else {
    document.getElementById("data-note").textContent = "Dados de results/benchmark.csv.";
  }
})();
