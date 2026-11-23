(() => {
  "use strict";
  const input = document.querySelector("#audio-file");
  const dropzone = document.querySelector("#dropzone");
  const fileInfo = document.querySelector("#file-info");
  const startButton = document.querySelector("#start-analysis");
  const status = document.querySelector("#upload-status");
  const menuButton = document.querySelector("#menu-toggle");
  const sidebar = document.querySelector("#sidebar");
  let selectedFile = null;

  const allowedExtensions = new Set(["mp3", "wav", "flac", "m4a", "ogg"]);
  const formatBytes = (bytes) => {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  };

  function acceptFile(file) {
    if (!file) return;
    const extension = file.name.split(".").pop().toLowerCase();
    if (!allowedExtensions.has(extension) || !file.type.startsWith("audio/")) {
      selectedFile = null;
      startButton.disabled = true;
      fileInfo.hidden = true;
      status.textContent = "Formato não reconhecido. Selecione MP3, WAV, FLAC, M4A ou OGG.";
      return;
    }
    selectedFile = file;
    fileInfo.hidden = false;
    fileInfo.textContent = file.name + " · " + formatBytes(file.size);
    startButton.disabled = false;
    status.textContent = "Arquivo validado localmente. A análise na nuvem ainda não está conectada.";
  }

  input.addEventListener("change", () => acceptFile(input.files[0]));
  ["dragenter", "dragover"].forEach((eventName) => dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.add("dragging");
  }));
  ["dragleave", "drop"].forEach((eventName) => dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropzone.classList.remove("dragging");
  }));
  dropzone.addEventListener("drop", (event) => {
    const file = event.dataTransfer.files[0];
    acceptFile(file);
  });
  startButton.addEventListener("click", () => {
    if (!selectedFile) return;
    status.textContent = "Arquivo pronto. Próxima etapa: conectar a API de processamento; nenhuma separação foi executada.";
  });
  menuButton.addEventListener("click", () => sidebar.classList.toggle("open"));
  document.querySelectorAll(".nav-item").forEach((link) => link.addEventListener("click", () => sidebar.classList.remove("open")));
})();