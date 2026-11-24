(() => {
  "use strict";
  const $ = (selector) => document.querySelector(selector);
  const input = $("#audio-file"), dropzone = $("#dropzone"), fileInfo = $("#file-info");
  const startButton = $("#start-analysis"), status = $("#upload-status");
  const menuButton = $("#menu-toggle"), sidebar = $("#sidebar");
  const apiInput = $("#api-url");
  let selectedFile = null, activeJobId = null, project = null, polling = false;

  const allowedExtensions = new Set(["mp3", "wav", "flac", "m4a", "ogg"]);
  const savedApi = localStorage.getItem("audiosplit-api-url") || "http://localhost:8000";
  apiInput.value = savedApi;

  function apiBase() {
    const value = apiInput.value.trim().replace(/\/+$/, "");
    if (!/^https?:\/\//i.test(value)) throw new Error("Informe um endereço HTTP ou HTTPS válido para a API.");
    return value;
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
      setStatus("Áudio recebido. Processamento iniciado.");
      await pollJob(base, activeJobId);
    } catch (error) {
      setStatus(error.message || "Não foi possível conectar à API.", true);
      $("#job-message").textContent = "Falha no envio ou na conexão.";
      polling = false; startButton.disabled = false;
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
      wrapper.append(title, audio); $("#stem-players").append(wrapper);
    });
    const words = result.transcription?.words || [];
    $("#lyrics-editor").value = words.map(item => item.label).join(" ");
    $("#lyric-meta").textContent = words.length + " tokens reconhecidos · " + (result.transcription?.language || "idioma não identificado") + ". Os tempos por palavra permanecem no JSON.";
    renderChordRows(result.chords || []);\n    renderTimeline(result);
    const bpm = result.rhythm?.tempo_bpm;\n    $("#timeline-status").textContent = words.length + " palavras · " + (result.chords || []).length + " eventos" + (bpm ? " · " + bpm + " BPM" : "");
    $("#export-status").textContent = "Projeto pronto para revisão";
    $("#save-edits").disabled = false; $("#export-json").disabled = false; $("#export-text").disabled = false;
    $("#edit-status").textContent = result.chord_note || "Revise os eventos antes de exportar.";
  }
  function renderLyricChordView(result) {
    const container = $("#lyric-chord-view"); container.replaceChildren();
    const words = result.transcription?.words || [];
    const chords = result.chords || [];
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
  function renderChordRows(chords) {
    const body = $("#chord-rows"); body.replaceChildren();
    $("#chord-count").textContent = chords.length + (chords.length === 1 ? " acorde" : " acordes");
    if (!chords.length) {
      const row = document.createElement("tr"), cell = document.createElement("td");
      cell.colSpan = 3; cell.className = "empty-cell"; cell.textContent = "Nenhum evento harmônico confiável foi identificado.";
      row.append(cell); body.append(row); return;
    }
    chords.forEach((chord, index) => {
      const row = document.createElement("tr");
      const timeCell = document.createElement("td"), chordCell = document.createElement("td"), confCell = document.createElement("td");
      const time = document.createElement("input"); time.type = "number"; time.min = "0"; time.step = "0.01"; time.value = chord.start; time.dataset.index = index; time.dataset.field = "start";
      const label = document.createElement("input"); label.type = "text"; label.value = chord.label; label.maxLength = 24; label.dataset.index = index; label.dataset.field = "label";
      timeCell.append(time); chordCell.append(label); confCell.textContent = chord.confidence == null ? "—" : Math.round(chord.confidence * 100) + "%";
      row.append(timeCell, chordCell, confCell); body.append(row);
    });
  }
  function applyEdits() {
    if (!project) return;
    const words = project.transcription?.words || [];
    const editedWords = $("#lyrics-editor").value.trim().split(/\s+/).filter(Boolean);
    if (editedWords.length === words.length) {
      words.forEach((word, index) => { word.label = editedWords[index]; });
    } else {
      project.transcription.edited_text = $("#lyrics-editor").value.trim();
      project.transcription.edit_note = "Texto editado sem correspondência token a token; timestamps originais preservados.";
    }
    document.querySelectorAll("#chord-rows input").forEach((field) => {
      const index = Number(field.dataset.index), key = field.dataset.field;
      if (project.chords[index]) project.chords[index][key] = key === "start" ? Number(field.value) : field.value.trim();
    });
    project.chords.sort((a, b) => a.start - b.start);
    $("#edit-status").textContent = "Revisões aplicadas nesta sessão. Exporte o projeto para salvá-las.";
    renderChordRows(project.chords);\n    renderLyricChordView(project);\n    renderTimeline(project);
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
  function exportText() {
    if (!project) return;
    const events = [
      ...(project.transcription?.words || []).map(item => ({ ...item, type: "LETRA" })),
      ...(project.chords || []).map(item => ({ ...item, type: "ACORDE" }))
    ].sort((a, b) => a.start - b.start);
    const lines = events.map(item => item.start.toFixed(2) + "s\t" + item.type + "\t" + item.label);
    downloadFile("audiosplit-eventos-" + project.job_id + ".txt", lines.join("\n"), "text/plain;charset=utf-8");
  }

  input.addEventListener("change", () => acceptFile(input.files[0]));
  ["dragenter", "dragover"].forEach(name => dropzone.addEventListener(name, event => { event.preventDefault(); dropzone.classList.add("dragging"); }));
  ["dragleave", "drop"].forEach(name => dropzone.addEventListener(name, event => { event.preventDefault(); dropzone.classList.remove("dragging"); }));
  dropzone.addEventListener("drop", event => acceptFile(event.dataTransfer.files[0]));
  startButton.addEventListener("click", startAnalysis);
  $("#save-api").addEventListener("click", () => {
    try { const value = apiBase(); localStorage.setItem("audiosplit-api-url", value); setStatus("Endereço da API salvo."); }
    catch (error) { setStatus(error.message, true); }
  });
  $("#save-edits").addEventListener("click", applyEdits);
  $("#export-json").addEventListener("click", exportJson);
  $("#export-text").addEventListener("click", exportText);
  menuButton.addEventListener("click", () => sidebar.classList.toggle("open"));
  document.querySelectorAll(".nav-item").forEach(link => link.addEventListener("click", () => sidebar.classList.remove("open")));
})();