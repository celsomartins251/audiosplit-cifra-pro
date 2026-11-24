(() => {
  "use strict";
  const $ = (selector) => document.querySelector(selector);
  const input = $("#audio-file"), dropzone = $("#dropzone"), fileInfo = $("#file-info");
  const startButton = $("#start-analysis"), status = $("#upload-status");
  const menuButton = $("#menu-toggle"), sidebar = $("#sidebar");
  const apiInput = $("#api-url");
  let selectedFile = null, activeJobId = null, project = null, polling = false;

  const allowedExtensions = new Set(["mp3", "wav", "flac", "m4a", "ogg"]);
  const hostedFrontend = location.hostname.endsWith("github.io");
  const localApiDefault = hostedFrontend ? "" : "http://localhost:8000";
  const savedApi = localStorage.getItem("audiosplit-api-url") || localApiDefault;
  apiInput.value = savedApi;
  apiInput.placeholder = hostedFrontend ? "https://endereco-publico-da-api" : "http://localhost:8000";
  $("#job-id-input").value = localStorage.getItem("audiosplit-last-job") || "";

  function apiBase() {
    const value = apiInput.value.trim().replace(/\/+$/, "");
    let parsed;
    try {
      parsed = new URL(value);
    } catch {
      throw new Error(hostedFrontend
        ? "Informe um endereço HTTPS válido para o servidor da API."
        : "Informe um endereço HTTP ou HTTPS válido para a API.");
    }
    if (!["http:", "https:"].includes(parsed.protocol) || !parsed.hostname) {
      throw new Error("A API precisa usar um endereço HTTP ou HTTPS válido.");
    }
    if (parsed.username || parsed.password || parsed.search || parsed.hash) {
      throw new Error("Informe somente o endereço-base da API, sem credenciais, parâmetros ou fragmentos.");
    }
    if (hostedFrontend && parsed.protocol !== "https:") {
      throw new Error("O servidor precisa usar HTTPS para funcionar com o site público.");
    }
    const host = parsed.hostname.toLowerCase().replace(/^\[|\]$/g, "");
    const loopback = host === "localhost" || host.endsWith(".localhost") ||
      host === "127.0.0.1" || host === "::1";
    if (hostedFrontend && loopback) {
      throw new Error("No site público, localhost aponta para o próprio aparelho. Informe o endereço público do servidor.");
    }
    return parsed.origin + parsed.pathname.replace(/\/+$/, "");
  }
  function setStatus(message, isError = false) {
    status.textContent = message;
    status.classList.toggle("error-text", isError);
  }
  function formatBytes(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  }
  function acceptFile(file) {
    if (!file) return;
    const extension = file.name.split(".").pop().toLowerCase();
    if (!allowedExtensions.has(extension) || (file.type && !file.type.startsWith("audio/"))) {
      selectedFile = null; startButton.disabled = true; fileInfo.hidden = true;
      setStatus("Formato inválido. Use MP3, WAV, FLAC, M4A ou OGG.", true); return;
    }
    if (file.size > 250 * 1024 * 1024) {
      selectedFile = null; startButton.disabled = true;
      setStatus("O arquivo excede o limite inicial de 250 MB.", true); return;
    }
    selectedFile = file; fileInfo.hidden = false;
    const sourcePlayer = $("#source-player");
    if (sourcePlayer.dataset.objectUrl) URL.revokeObjectURL(sourcePlayer.dataset.objectUrl);
    sourcePlayer.dataset.objectUrl = URL.createObjectURL(file);
    sourcePlayer.src = sourcePlayer.dataset.objectUrl; sourcePlayer.hidden = false;
    fileInfo.textContent = file.name + " · " + formatBytes(file.size);
    startButton.disabled = false;
    setStatus("Arquivo selecionado. Pronto para enviar ao servidor.");
  }
  function setProgress(progress, message) {
    $("#job-progress").hidden = false;
    $("#progress-fill").style.width = Math.max(0, Math.min(100, progress || 0)) + "%";
    $("#progress-value").textContent = Math.round(progress || 0) + "%";
    $("#job-message").textContent = message || "Processando…";
  }
  async function startAnalysis() {
    if (!selectedFile || polling) return;
    let base;
    try { base = apiBase(); } catch (error) { setStatus(error.message, true); return; }
    startButton.disabled = true; polling = true;
    setStatus("Enviando áudio…"); setProgress(0, "Enviando arquivo");
    try {
      const form = new FormData(); form.append("audio", selectedFile, selectedFile.name);
      const response = await fetch(base + "/v1/jobs", { method: "POST", body: form });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.detail || "Falha ao enviar o áudio (" + response.status + ").");
      activeJobId = payload.job_id;
      $("#job-id-input").value = activeJobId;
      localStorage.setItem("audiosplit-last-job", activeJobId);
      setStatus("Áudio recebido. Processamento iniciado.");
      await pollJob(base, activeJobId);
    } catch (error) {
      setStatus(error.message || "Não foi possível conectar à API.", true);
      $("#job-message").textContent = "Falha no envio ou na conexão.";
      polling = false; startButton.disabled = false;
    }
  }
  async function loadProject() {
    const jobId = $("#job-id-input").value.trim();
    if (!jobId) { setStatus("Informe o identificador do projeto.", true); return; }
    let base;
    try { base = apiBase(); } catch (error) { setStatus(error.message, true); return; }
    setStatus("Abrindo projeto salvo…");
    try {
      const response = await fetch(base + "/v1/jobs/" + encodeURIComponent(jobId));
      const job = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(job.detail || "Projeto não encontrado.");
      activeJobId = jobId; localStorage.setItem("audiosplit-last-job", jobId);
      const player = $("#source-player");
      if (player.dataset.objectUrl) URL.revokeObjectURL(player.dataset.objectUrl);
      player.removeAttribute("src");
      player.src = base + "/v1/jobs/" + encodeURIComponent(jobId) + "/source";
      player.hidden = false;
      if (job.status === "completed") {
        const resultResponse = await fetch(base + "/v1/jobs/" + encodeURIComponent(jobId) + "/result");
        const result = await resultResponse.json();
        if (!resultResponse.ok) throw new Error(result.detail || "Resultado indisponível.");
        project = result; renderProject(base, result);
        if (!$("#source-player").src) $("#source-player").src = base + "/v1/jobs/" + encodeURIComponent(jobId) + "/source";
        setProgress(100, "Projeto carregado.");
        setStatus("Projeto reaberto. Você pode continuar a revisão.");
      } else if (job.status === "queued" || job.status === "processing") {
        polling = true; startButton.disabled = true;
        await pollJob(base, jobId);
      } else {
        throw new Error(job.error_message || job.message || "Este processamento terminou com falha.");
      }
    } catch (error) {
      polling = false; startButton.disabled = false;
      setStatus(error.message || "Não foi possível abrir o projeto.", true);
    }
  }
  async function pollJob(base, jobId) {
    while (polling) {
      const response = await fetch(base + "/v1/jobs/" + encodeURIComponent(jobId));
      const job = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(job.detail || "Não foi possível consultar o processamento.");
      setProgress(job.progress || 0, job.message || job.status);
      if (job.status === "completed") {
        const resultResponse = await fetch(base + "/v1/jobs/" + encodeURIComponent(jobId) + "/result");
        const result = await resultResponse.json();
        if (!resultResponse.ok) throw new Error(result.detail || "Resultado não disponível.");
        project = result; renderProject(base, result);
        setStatus("Análise concluída. Revise os resultados automáticos.");
        polling = false; startButton.disabled = false; return;
      }
      if (job.status === "failed") {
        throw new Error((job.error_code || "PROCESSING_FAILED") + ": " + (job.error_message || job.message || "Falha no processamento."));
      }
      await new Promise(resolve => setTimeout(resolve, 2500));
    }
  }
  function renderProject(base, result) {
    const stems = result.separation?.stems || {};
    $("#stems-status").textContent = Object.keys(stems).length + " faixas geradas";
    $("#stem-players").replaceChildren();
    document.querySelectorAll(".stem").forEach(row => {
      const name = row.dataset.stem, available = Boolean(stems[name]);
      row.querySelector(".pending").textContent = available ? "Disponível" : "Indisponível";
      row.querySelector(".pending").classList.toggle("ready", available);
    });
    Object.entries(stems).forEach(([name, stem]) => {
      const wrapper = document.createElement("div"); wrapper.className = "stem-player";
      const title = document.createElement("strong"); title.textContent = name.toUpperCase();
      const audio = document.createElement("audio"); audio.controls = true; audio.preload = "none";
      audio.src = base + stem.download_path;
      const download = document.createElement("button"); download.type = "button"; download.className = "secondary-button"; download.textContent = "Baixar WAV"; download.addEventListener("click", async () => { download.disabled = true; try { const response = await fetch(base + stem.download_path); if (!response.ok) throw new Error("Falha ao baixar " + name + "."); const url = URL.createObjectURL(await response.blob()); const anchor = document.createElement("a"); anchor.href = url; anchor.download = name + ".wav"; document.body.append(anchor); anchor.click(); anchor.remove(); setTimeout(() => URL.revokeObjectURL(url), 30000); } catch (error) { setStatus(error.message, true); } finally { download.disabled = false; } }); wrapper.append(title, audio, download); $("#stem-players").append(wrapper);
    });
    const words = result.transcription?.words || [];
    $("#lyrics-editor").value = result.transcription?.edited_text || words.map(item => item.label).join(" ");
    $("#lyric-meta").textContent = words.length + " tokens reconhecidos · " + (result.transcription?.language || "idioma não identificado") + " · " + (result.transcription?.alignment_method || "timestamp ASR") + ". " + (result.transcription?.alignment_note || "Tempos estimados; revise o canto.");
    renderWordRows(words);
    renderChordRows(result.chords || []);
    renderLyricChordView(result);
    renderTimeline(result);
    const bpm = result.rhythm?.tempo_bpm;
    $("#timeline-status").textContent = words.length + " palavras · " + (result.chords || []).length + " eventos" + (bpm ? " · " + bpm + " BPM" : "");
    $("#export-status").textContent = "Projeto pronto para revisão";
    $("#save-edits").disabled = false; $("#export-json").disabled = false; $("#export-text").disabled = false; $("#export-chordpro").disabled = false; $("#export-pdf").disabled = false; $("#export-stems").disabled = false;
    $("#edit-status").textContent = result.chord_note || "Revise os eventos antes de exportar.";
  }
  function renderLyricChordView(result) {
    const container = $("#lyric-chord-view"); container.replaceChildren();
    const words = result.transcription?.words || [];
    const chords = result.chords || [];
    if (result.transcription?.edited_text) {
      const text = document.createElement("span"); text.className = "unmapped-lyrics";
      text.textContent = result.transcription.edited_text;
      const note = document.createElement("small"); note.textContent = "Texto reescrito sem alinhamento token a token; timestamps anteriores foram preservados.";
      container.append(text, note); return;
    }
    if (!words.length) {
      const empty = document.createElement("span"); empty.className = "empty-cell";
      empty.textContent = "Sem palavras com timestamp para posicionar as cifras.";
      container.append(empty); return;
    }
    const assigned = new Map();
    chords.forEach(chord => {
      const index = words.findIndex(word => Number(word.end) >= Number(chord.start));
      if (index >= 0) {
        if (!assigned.has(index)) assigned.set(index, []);
        assigned.get(index).push(chord);
      }
    });
    words.forEach((word, index) => {
      const token = document.createElement("span"); token.className = "lyric-token";
      const chordLine = document.createElement("span"); chordLine.className = "lyric-chord-labels";
      (assigned.get(index) || []).forEach(chord => {
        const badge = document.createElement("strong"); badge.textContent = chord.label; chordLine.append(badge);
      });
      const wordLabel = document.createElement("span"); wordLabel.className = "lyric-word"; wordLabel.textContent = word.label;
      const time = document.createElement("small"); time.textContent = formatTime(word.start);
      token.append(chordLine, wordLabel, time); container.append(token);
    });
  }
  function formatTime(seconds) {
    const value = Math.max(0, Number(seconds) || 0);
    return Math.floor(value / 60) + ":" + String(Math.floor(value % 60)).padStart(2, "0") + "." + String(Math.floor((value % 1) * 10));
  }
  function renderTimeline(result) {
    const container = $("#timeline-events"); container.replaceChildren();
    const words = result.transcription?.words || [];
    const events = [
      ...words.map((item, index) => ({ ...item, kind: "word", index })),
      ...(result.chords || []).map((item, index) => ({ ...item, kind: "chord", index }))
    ].sort((a, b) => a.start - b.start);
    if (!events.length) {
      const empty = document.createElement("span"); empty.className = "empty-cell"; empty.textContent = "Nenhum evento temporal foi reconhecido.";
      container.append(empty); return;
    }
    events.forEach(event => {
      const button = document.createElement("button");
      button.type = "button"; button.className = "timeline-event " + event.kind;
      button.dataset.start = event.start; button.dataset.end = event.end;
      const time = document.createElement("small"); time.textContent = formatTime(event.start);
      const label = document.createElement("strong"); label.textContent = event.kind === "chord" ? event.label : event.label.trim();
      const type = document.createElement("em"); type.textContent = event.kind === "chord" ? "ACORDE" : "LETRA";
      button.append(time, label, type);
      button.addEventListener("click", () => {
        const player = $("#source-player"); player.currentTime = Number(event.start);
        player.play().catch(() => {});
      });
      container.append(button);
    });
  }
  $("#source-player").addEventListener("timeupdate", () => {
    const time = $("#source-player").currentTime;
    document.querySelectorAll(".timeline-event").forEach(item => {
      const start = Number(item.dataset.start), end = Number(item.dataset.end);
      item.classList.toggle("playing", time >= start && time <= end);
    });
  });
  function renderWordRows(words) {
    const body = $("#word-rows"); body.replaceChildren();
    $("#word-count").textContent = words.length + (words.length === 1 ? " palavra" : " palavras");
    if (!words.length) {
      const row = document.createElement("tr"), cell = document.createElement("td");
      cell.colSpan = 3; cell.className = "empty-cell"; cell.textContent = "Nenhuma palavra com timestamp.";
      row.append(cell); body.append(row); return;
    }
    words.forEach((word, index) => {
      const row = document.createElement("tr");
      const startCell = document.createElement("td"), endCell = document.createElement("td"), labelCell = document.createElement("td");
      for (const [cell, field, value] of [[startCell, "start", word.start], [endCell, "end", word.end]]) {
        const input = document.createElement("input"); input.type = "number"; input.min = "0"; input.step = "0.01";
        input.value = value; input.dataset.index = index; input.dataset.field = field; cell.append(input);
      }
      labelCell.textContent = word.label;
      row.append(startCell, endCell, labelCell); body.append(row);
    });
  }
  function renderChordRows(chords) {
    const body = $("#chord-rows"); body.replaceChildren();
    $("#chord-count").textContent = chords.length + (chords.length === 1 ? " acorde" : " acordes");
    if (!chords.length) {
      const row = document.createElement("tr"), cell = document.createElement("td");
      cell.colSpan = 4; cell.className = "empty-cell"; cell.textContent = "Nenhum evento harmônico confiável foi identificado."
      row.append(cell); body.append(row); return;
    }
    chords.forEach((chord, index) => {
      const row = document.createElement("tr");
      const startCell = document.createElement("td"), endCell = document.createElement("td"), chordCell = document.createElement("td"), confCell = document.createElement("td");
      for (const [cell, field, value] of [[startCell, "start", chord.start], [endCell, "end", chord.end]]) {
        const input = document.createElement("input"); input.type = "number"; input.min = "0"; input.step = "0.01";
        input.value = value; input.dataset.index = index; input.dataset.field = field; cell.append(input);
      }
      const label = document.createElement("input"); label.type = "text"; label.value = chord.label; label.maxLength = 24;
      label.dataset.index = index; label.dataset.field = "label"; chordCell.append(label);
      confCell.textContent = chord.confidence == null ? "—" : Math.round(chord.confidence * 100) + "%";
      row.append(startCell, endCell, chordCell, confCell); body.append(row);
    });
  }
  async function applyEdits() {
    if (!project) return;
    const words = project.transcription?.words || [];
    const editedWords = $("#lyrics-editor").value.trim().split(/\s+/).filter(Boolean);
    if (editedWords.length === words.length) {
      delete project.transcription.edited_text;
      delete project.transcription.edit_note;
      words.forEach((word, index) => { word.label = editedWords[index]; });
    } else {
      project.transcription.edited_text = $("#lyrics-editor").value.trim();
      project.transcription.edit_note = "Texto editado sem correspondência token a token; timestamps originais preservados.";
    }
    document.querySelectorAll("#word-rows input").forEach((field) => {
      const index = Number(field.dataset.index), key = field.dataset.field;
      if (words[index]) words[index][key] = key === "start" || key === "end" ? Number(field.value) : field.value.trim();
    });
    document.querySelectorAll("#chord-rows input").forEach((field) => {
      const index = Number(field.dataset.index), key = field.dataset.field;
      if (project.chords[index]) project.chords[index][key] = key === "start" || key === "end" ? Number(field.value) : field.value.trim();
    });
    project.chords.sort((a, b) => a.start - b.start);
    words.sort((a, b) => a.start - b.start);
    renderWordRows(words);
    renderChordRows(project.chords);
    renderLyricChordView(project);
    renderTimeline(project);
    $("#edit-status").textContent = "Revisões aplicadas. Salvando no servidor…";
    try {
      const response = await fetch(apiBase() + "/v1/jobs/" + encodeURIComponent(project.job_id) + "/result", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(project)
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.detail || "Falha ao salvar revisões.");
      $("#edit-status").textContent = "Revisões salvas no servidor.";
    } catch (error) {
      $("#edit-status").textContent = "Revisões mantidas nesta sessão, mas não salvas no servidor: " + error.message;
    }
  }
  function downloadFile(filename, content, mime) {
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = filename;
    document.body.append(anchor); anchor.click(); anchor.remove(); URL.revokeObjectURL(url);
  }
  function exportJson() {
    if (!project) return;
    downloadFile("audiosplit-cifra-pro-" + project.job_id + ".json", JSON.stringify(project, null, 2), "application/json");
  }
  function exportChordPro() {
    if (!project) return;
    const words = project.transcription?.words || [];
    const editedText = project.transcription?.edited_text;
    if (!words.length) {
      $("#edit-status").textContent = "Não há palavras com timestamp para gerar ChordPro.";
      return;
    }
    if (editedText && editedText.trim().split(/\s+/).length !== words.length) {
      $("#edit-status").textContent = "A letra foi reescrita com outra quantidade de palavras. Ajuste o alinhamento palavra a palavra antes de exportar ChordPro.";
      return;
    }
    const assigned = new Map();
    (project.chords || []).forEach(chord => {
      const index = words.findIndex(word => Number(word.end) >= Number(chord.start));
      if (index >= 0) {
        if (!assigned.has(index)) assigned.set(index, []);
        assigned.get(index).push(chord);
      }
    });
    const lyrics = words.map((word, index) => {
      const markers = (assigned.get(index) || []).map(chord => "[" + chord.label + "]").join("");
      return markers + word.label;
    }).join(" ");
    const title = (project.audio?.source_filename || selectedFile?.name || "AudioSplit project").replace(/\.[^.]+$/, "").replace(/[{}\r\n]/g, " ");
    const content = "{title: " + title + "}\n{comment: ChordPro gerado pelo AudioSplit & Cifra Pro; cifras associadas à palavra temporalmente mais próxima. Consulte o JSON para timestamps exatos.}\n\n" + lyrics + "\n";
    downloadFile("audiosplit-" + project.job_id + ".pro", content, "text/plain;charset=utf-8");
  }
  function exportText() {
    if (!project) return;
    const events = [
      ...(project.transcription?.words || []).map(item => ({ ...item, type: "LETRA" })),
      ...(project.chords || []).map(item => ({ ...item, type: "ACORDE" }))
    ].sort((a, b) => a.start - b.start);
    const lines = events.map(item => item.start.toFixed(2) + "s\t" + item.type + "\t" + item.label);
    downloadFile("audiosplit-eventos-" + project.job_id + ".txt", lines.join("\n"), "text/plain;charset=utf-8");
  }


  function exportPdf() {
    if (!project) return;
    const words = project.transcription?.words || [], chords = project.chords || [], assigned = new Map();
    chords.forEach(chord => {
      const index = words.findIndex(word => Number(word.end) >= Number(chord.start));
      if (index >= 0) { if (!assigned.has(index)) assigned.set(index, []); assigned.get(index).push(chord); }
    });
    const esc = value => String(value ?? "").replace(/[&<>"]/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[ch]));
    const title = esc((project.audio?.source_filename || selectedFile?.name || "Análise musical").replace(/\.[^.]+$/, ""));
    const lyricRows = words.length ? words.map((word, index) => '<div class="token"><b>' + (assigned.get(index) || []).map(c => esc(c.label)).join(" · ") + '</b><span>' + esc(word.label) + '</span><small>' + formatTime(word.start) + '</small></div>').join("") : '<p>' + esc(project.transcription?.edited_text || "Sem transcrição disponível.") + '</p>';
    const chordRows = chords.map(c => '<tr><td>' + Number(c.start).toFixed(2) + 's</td><td>' + Number(c.end).toFixed(2) + 's</td><td><b>' + esc(c.label) + '</b></td></tr>').join("");
    const wordRows = words.map(w => '<tr><td>' + Number(w.start).toFixed(2) + 's</td><td>' + Number(w.end).toFixed(2) + 's</td><td>' + esc(w.label) + '</td></tr>').join("");
    const win = window.open("", "_blank");
    if (!win) { $("#edit-status").textContent = "Pop-up bloqueado. Permita pop-ups para este site e tente novamente."; return; }
    win.document.write('<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>' + title + ' - AudioSplit</title><style>body{font:12px Arial,sans-serif;color:#171717;margin:20mm}h1{font-size:20px}h2{font-size:15px;margin-top:24px}.meta{color:#555}.lyrics{display:flex;flex-wrap:wrap;gap:12px 8px;margin:18px 0}.token{display:flex;flex-direction:column;min-width:48px;gap:3px}.token b{color:#946c12;min-height:14px}.token small{color:#777;font-size:9px}table{width:100%;border-collapse:collapse;margin-top:8px}td,th{border-bottom:1px solid #ccc;padding:6px;text-align:left}th{background:#eee}@media print{body{margin:15mm}}</style></head><body><h1>' + title + '</h1><p class="meta">AudioSplit & Cifra Pro · Projeto ' + esc(project.job_id) + '</p><h2>Letra com cifras posicionadas por evento temporal</h2><div class="lyrics">' + lyricRows + '</div><h2>Eventos harmônicos</h2><table><thead><tr><th>Início</th><th>Fim</th><th>Acorde</th></tr></thead><tbody>' + chordRows + '</tbody></table><h2>Alinhamento palavra por palavra</h2><table><thead><tr><th>Início</th><th>Fim</th><th>Palavra</th></tr></thead><tbody>' + wordRows + '</tbody></table><p class="meta">Tempos e acordes são estimativas automáticas e devem ser revisados auditivamente.</p><script>window.onload=()=>window.print();<\/script></body></html>');
    win.document.close();
  }
  async function exportStemsZip() {
    if (!project?.job_id) return;
    let base; try { base = apiBase(); } catch (error) { setStatus(error.message, true); return; }
    const button = $("#export-stems"); button.disabled = true; button.textContent = "Preparando ZIP…";
    try {
      const response = await fetch(base + "/v1/jobs/" + encodeURIComponent(project.job_id) + "/stems.zip");
      if (!response.ok) { const payload = await response.json().catch(() => ({})); throw new Error(payload.detail || "Não foi possível preparar o ZIP."); }
      const url = URL.createObjectURL(await response.blob()), anchor = document.createElement("a");
      anchor.href = url; anchor.download = "audiosplit-stems-" + project.job_id + ".zip";
      document.body.append(anchor); anchor.click(); anchor.remove(); setTimeout(() => URL.revokeObjectURL(url), 30000);
      setStatus("Pacote ZIP das faixas gerado.");
    } catch (error) { setStatus(error.message, true); }
    finally { button.disabled = false; button.textContent = "Baixar faixas separadas (ZIP)"; }
  }

  input.addEventListener("change", () => acceptFile(input.files[0]));
  ["dragenter", "dragover"].forEach(name => dropzone.addEventListener(name, event => { event.preventDefault(); dropzone.classList.add("dragging"); }));
  ["dragleave", "drop"].forEach(name => dropzone.addEventListener(name, event => { event.preventDefault(); dropzone.classList.remove("dragging"); }));
  dropzone.addEventListener("drop", event => acceptFile(event.dataTransfer.files[0]));
  startButton.addEventListener("click", startAnalysis);
  $("#load-project").addEventListener("click", loadProject);
  $("#save-api").addEventListener("click", () => {
    try { const value = apiBase(); localStorage.setItem("audiosplit-api-url", value); setStatus("Endereço da API salvo."); }
    catch (error) { setStatus(error.message, true); }
  });
  $("#save-edits").addEventListener("click", applyEdits);
  $("#export-json").addEventListener("click", exportJson);
  $("#export-text").addEventListener("click", exportText);
  $("#export-chordpro").addEventListener("click", exportChordPro);
  $("#export-pdf").addEventListener("click", exportPdf);
  $("#export-stems").addEventListener("click", exportStemsZip);
  menuButton.addEventListener("click", () => sidebar.classList.toggle("open"));
  document.querySelectorAll(".nav-item").forEach(link => link.addEventListener("click", () => sidebar.classList.remove("open")));
})();