document.addEventListener("DOMContentLoaded", () => {
  // Initialize CodeMirror with combined options
  const codeEditor = CodeMirror.fromTextArea(document.getElementById("manim-code"), {
    mode: "python",
    theme: "dracula",
    lineNumbers: true,
    indentUnit: 4,
    tabSize: 4,
    smartIndent: true,
    indentWithTabs: false,
    lineWrapping: true,
    matchBrackets: true,
    autoCloseBrackets: true,
    extraKeys: {
      Tab: cm => cm.somethingSelected() ? cm.indentSelection("add") : cm.replaceSelection("    ", "end", "+input"),
      "Ctrl-/": "toggleComment",
      "Cmd-/": "toggleComment",
    },
  });

  // Gather DOM elements
  const els = {
    executeButton: document.getElementById("execute-button"),
    generateButton: document.getElementById("generate-button"),
    clearChatButton: document.getElementById("clear-chat-btn"),
    toggleEditorButton: document.getElementById("toggle-editor-button"),
    toggleEditorText: document.getElementById("toggle-editor-text"),
    previewShowEditor: document.getElementById("preview-show-editor"),
    codeEditorContainer: document.getElementById("code-editor-container"),
    codePreview: document.getElementById("code-preview"),
    codePreviewLines: document.getElementById("code-preview-lines"),
    codeEditor: codeEditor,
    outputVideo: document.getElementById("output-video"),
    statusMessage: document.getElementById("status-message"),
    statusText: document.getElementById("status-text"),
    statusContainer: document.getElementById("status-container"),
    manimPrompt: document.getElementById("manim-prompt"),
    executeSpinner: document.getElementById("execute-spinner"),
    generateSpinner: document.getElementById("generate-spinner"),
    generatePromptSpinner: document.getElementById("generate-prompt-spinner"),
    videoOverlay: document.getElementById("video-overlay"),
    chatContainer: document.getElementById("chat-container"),
    logDisplay: document.getElementById("log-display"),
    logLines: document.getElementById("log-lines"),
  };

  // UI utility functions
  const toggleEditor = () => {
    const isVisible = !els.codeEditorContainer.classList.contains('d-none');
    
    els.codeEditorContainer.classList.toggle('d-none', isVisible);
    els.codePreview.classList.toggle('d-none', !isVisible);
    els.toggleEditorText.textContent = isVisible ? 'Show Editor' : 'Hide Editor';
    
    if (!isVisible) els.codeEditor.refresh();
  };
  
  const updateCodePreview = () => {
    const code = els.codeEditor.getValue();
    const lineCount = code.split('\n').filter(line => line.trim()).length;
    els.codePreviewLines.textContent = lineCount;
  };

  const toggleLoading = (type, state) => {
    if (state) {
      els[`${type}Spinner`].classList.remove("d-none");
    } else {
      els[`${type}Spinner`].classList.add("d-none");
    }
    els[`${type}Button`].disabled = state;
    if (type === "execute") {
      if (state) {
        els.videoOverlay.classList.remove("d-none");
        els.videoOverlay.classList.add("d-flex");
      } else {
        els.videoOverlay.classList.add("d-none");
        els.videoOverlay.classList.remove("d-flex");
      }
    }
  };

  const showStatus = (type, message, timeout = 3000) => {
    els.statusContainer.className = `px-3 py-2 rounded bg-${type}-custom`;
    els.statusText.className = `small mb-0`;
    els.statusText.textContent = message;
    els.statusMessage.classList.remove("d-none");
    if (timeout) setTimeout(() => els.statusMessage.classList.add("d-none"), timeout);
  };

  // Chat functions
  const addChatMessage = (message, role) => {
    const messageDiv = document.createElement("div");
    messageDiv.className = role === "user" ? "user-message p-3" : "assistant-message p-3";

    if (role === "user") {
      messageDiv.textContent = message;
    } else {
      const numLines = message.split("\n").filter(line => line.trim() !== "").length;
      messageDiv.innerHTML = `<div class="code-preview">
        <p class="small font-monospace d-flex align-items-center">
          <span class="me-2" style="color: #a5b4fc"><i>Code generated:</i></span>
          <span class="bg-dark bg-opacity-50 px-2 py-1 rounded">${numLines} lines</span>
        </p>
      </div>`;
    }

    // Remove the empty state if it exists
    const emptyState = els.chatContainer.querySelector(".text-center.py-4");
    if (emptyState) {
      els.chatContainer.removeChild(emptyState);
    }

    els.chatContainer.appendChild(messageDiv);
    els.chatContainer.scrollTop = els.chatContainer.scrollHeight;
  };

  // API interactions
  const fetchChatHistory = async () => {
    try {
      const response = await fetch("/get_chat_history");
      if (response.ok) {
        const data = await response.json();
        if (data.chat_history && data.chat_history.length > 0) {
          els.chatContainer.innerHTML = "";
          data.chat_history.forEach((message) => {
            addChatMessage(message.content, message.role);
          });
        }
      }
    } catch (error) {
      console.error("Failed to fetch chat history:", error);
    }
  };

  const clearChatHistory = async () => {
    try {
      const response = await fetch("/clear_chat_history", {
        method: "POST",
      });
      if (response.ok) {
        els.chatContainer.innerHTML = `
          <div class="text-center py-4 opacity-50">
            <svg class="mb-2" width="32" height="32" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clip-rule="evenodd" />
            </svg>
            <span class="text-secondary small">Start a conversation with AutoManim</span>
          </div>
        `;
      }
    } catch (error) {
      console.error("Failed to clear chat history:", error);
    }
  };

  // Log display management
  let logEventSource = null;
  const maxLogLines = 8;  // Increased to show more important logs

  const addLogLine = (text, type = "info") => {
    // Skip unimportant logs
    if (text === "Animation frame rendered" && 
        document.querySelectorAll('.log-line:contains("Animation frame rendered")').length > 0) {
      // Just update the last "Animation frame rendered" line instead of adding a new one
      const renderingLines = document.querySelectorAll('.log-line.rendering-progress');
      if (renderingLines.length > 0) {
        renderingLines[renderingLines.length - 1].textContent += ".";
        return;
      }
    }

    // Create a new log line element
    const logLine = document.createElement("div");
    logLine.className = `log-line ${type}`;
    
    // Add special class for rendering progress
    if (text === "Animation frame rendered") {
      logLine.classList.add("rendering-progress");
    }
    
    logLine.textContent = text;

    // Add the new line
    els.logLines.appendChild(logLine);

    // Scroll to bottom
    els.logLines.scrollTop = els.logLines.scrollHeight;

    // Check if we need to remove old lines
    const lines = els.logLines.querySelectorAll(".log-line");
    if (lines.length > maxLogLines) {
      // Add fade-out class to the oldest line
      lines[0].classList.add("fade-out");

      // Remove after animation completes
      setTimeout(() => {
        if (lines[0].parentNode === els.logLines) {
          els.logLines.removeChild(lines[0]);
        }
      }, 500); // Match the CSS transition duration
    }
  };

  const startLogStream = () => {
    // Close any existing stream
    if (logEventSource) {
      logEventSource.close();
    }

    // Clear existing log lines
    els.logLines.innerHTML = "";

    // Show the log display
    els.logDisplay.classList.add("active");

    // Add an initial line
    addLogLine("Starting Manim animation...", "info");

    // Connect to SSE endpoint
    logEventSource = new EventSource("/stream_logs");

    logEventSource.onmessage = (event) => {
      if (event.data === "HEARTBEAT") {
        return; // Ignore heartbeats
      }

      if (event.data === "STREAM_END") {
        endLogStream();
        return;
      }

      if (event.data.startsWith("VIDEO_READY:")) {
        const videoUrl = event.data.substring("VIDEO_READY:".length);
        // Update video source and play
        els.outputVideo.querySelector("source").src =
          videoUrl + "?t=" + Date.now();
        els.outputVideo.load();
        els.outputVideo.play();

        // Add success message
        addLogLine("Animation rendered successfully!", "success");

        // Turn off loading state in UI
        toggleLoading("execute", false);
        showStatus("success", "Animation generated successfully!");

        // Keep log display visible
        return;
      }

      if (event.data.startsWith("ERROR:")) {
        // Handle errors
        const errorMessage = event.data.substring("ERROR:".length);
        addLogLine(errorMessage.trim(), "error");
        showStatus("danger", errorMessage.trim(), false);
        toggleLoading("execute", false);
        return;
      }

      // Regular log line
      addLogLine(event.data);
    };

    logEventSource.onerror = () => {
      console.error("Log stream error");
      addLogLine("Connection lost. Check server status.", "error");
      endLogStream();
      toggleLoading("execute", false);
    };
  };

  const endLogStream = () => {
    if (logEventSource) {
      logEventSource.close();
      logEventSource = null;
    }

    setTimeout(() => {
      addLogLine("Execution complete", "success");
    }, 500);
  };

  async function executeManim() {
    toggleLoading("execute", true);
    showStatus("primary", "Executing Manim code...", false);
    startLogStream();

    try {
      const res = await fetch("/execute_manim", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: els.codeEditor.getValue() }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to execute Manim code");
    } catch (e) {
      addLogLine(e.message, "error");
      showStatus("danger", e.message, false);
      toggleLoading("execute", false);
      els.logDisplay.classList.remove("active");
      endLogStream();
    }
  }

  async function generateManim() {
    if (!els.manimPrompt.value.trim())
      return showStatus("danger", "Please enter a prompt", false);
      
    toggleLoading("generate", true);
    showStatus("primary", "Generating Manim code...", false);
    addChatMessage(els.manimPrompt.value.trim(), "user");

    try {
      const res = await fetch("/generate_manim_code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ manimPrompt: els.manimPrompt.value }),
      });
      
      const data = await res.json();
      if (res.ok) {
        els.codeEditor.setValue(data.code);
        els.codeEditor.refresh();
        updateCodePreview();
        addChatMessage(data.code, "assistant");
        els.manimPrompt.value = "";
        showStatus("success", "Code generated successfully!");
      } else throw new Error(data.error || "Failed to generate Manim code");
    } catch (e) {
      showStatus("danger", e.message, false);
    } finally {
      toggleLoading("generate", false);
    }
  }

  // Event listeners - using a common handler pattern
  const setupListeners = () => {
    els.executeButton.addEventListener("click", executeManim);
    els.generateButton.addEventListener("click", generateManim);
    els.toggleEditorButton.addEventListener("click", toggleEditor);
    els.previewShowEditor.addEventListener("click", () => {
      if (els.codeEditorContainer.classList.contains('d-none')) toggleEditor();
    });
    els.manimPrompt.addEventListener("keypress", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        generateManim();
      }
    });
    els.clearChatButton.addEventListener("click", clearChatHistory);
  };

  // Initialization
  const init = () => {
    updateCodePreview();
    fetchChatHistory();
    setupListeners();
  };

  init();
});
