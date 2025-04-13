document.addEventListener("DOMContentLoaded", () => {
  // Initialize CodeMirror
  const codeEditor = CodeMirror.fromTextArea(
    document.getElementById("manim-code"),
    {
      mode: "python",
      theme: "dracula",
      lineNumbers: true,
      indentUnit: 4,
      smartIndent: true,
      indentWithTabs: false,
      lineWrapping: true,
      matchBrackets: true,
      autoCloseBrackets: true,
      tabSize: 4,
      extraKeys: {
        Tab: function (cm) {
          if (cm.somethingSelected()) {
            cm.indentSelection("add");
          } else {
            cm.replaceSelection("    ", "end", "+input");
          }
        },
        "Ctrl-/": "toggleComment",
        "Cmd-/": "toggleComment",
      },
    }
  );

  const els = {
    executeButton: document.getElementById("execute-button"),
    generateButton: document.getElementById("generate-button"),
    clearChatButton: document.getElementById("clear-chat-btn"),
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
  };

  const toggleLoading = (type, state) => {
    els[`${type}Spinner`].classList.toggle("hidden", !state);
    els[`${type}Button`].disabled = state;
    if (type === "execute") els.videoOverlay.classList.toggle("hidden", !state);
  };

  const showStatus = (type, message, timeout = 3000) => {
    els.statusContainer.className = `px-4 py-3 rounded-md bg-${type}-900 bg-opacity-50`;
    els.statusText.className = `text-${type}-300`;
    els.statusText.textContent = message;
    els.statusMessage.classList.remove("hidden");
    if (timeout)
      setTimeout(() => els.statusMessage.classList.add("hidden"), timeout);
  };

  // Add a message to the chat container
  const addChatMessage = (message, role) => {
    const messageDiv = document.createElement("div");
    messageDiv.className =
      role === "user"
        ? "user-message p-3 text-white"
        : "assistant-message p-3 text-gray-200";

    if (role === "user") {
      messageDiv.textContent = message;
    } else {
      // Count lines and show compact preview
      const codeLines = message.split('\n').filter(line => line.trim() !== '');
      const numLines = codeLines.length;
      
      messageDiv.innerHTML = `<div class="code-preview">
        <p class="text-xs font-mono flex items-center">
          <span class="text-indigo-300 mr-2"><i>Code generated:</i></span>
          <span class="bg-gray-700 px-2 py-1 rounded">${numLines} lines</span>
        </p>
      </div>`;
    }

    els.chatContainer.appendChild(messageDiv);
    // Scroll to the bottom
    els.chatContainer.scrollTop = els.chatContainer.scrollHeight;
  };

  // Fetch chat history on page load
  const fetchChatHistory = async () => {
    try {
      const response = await fetch("/get_chat_history");
      if (response.ok) {
        const data = await response.json();
        if (data.chat_history && data.chat_history.length > 0) {
          // Clear initial message
          els.chatContainer.innerHTML = "";

          // Add messages to chat
          data.chat_history.forEach((message) => {
            addChatMessage(message.content, message.role);
          });
        }
      }
    } catch (error) {
      console.error("Failed to fetch chat history:", error);
    }
  };

  // Clear chat history
  const clearChatHistory = async () => {
    try {
      const response = await fetch("/clear_chat_history", {
        method: "POST",
      });
      if (response.ok) {
        els.chatContainer.innerHTML = `
          <div class="text-gray-500 text-center text-sm py-4">
            Start a conversation with AutoManim
          </div>
        `;
      }
    } catch (error) {
      console.error("Failed to clear chat history:", error);
    }
  };

  async function executeManim() {
    toggleLoading("execute", true);
    showStatus("indigo", "Executing Manim code...", false);
    try {
      const res = await fetch("/execute_manim", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: els.codeEditor.getValue() }),
      });
      const data = await res.json();
      if (res.ok) {
        els.outputVideo.querySelector("source").src =
          data.video_url + "?t=" + Date.now();
        els.outputVideo.load();
        els.outputVideo.play();
        showStatus("green", "Animation generated successfully!");
      } else throw new Error(data.error || "Failed to execute Manim code");
    } catch (e) {
      showStatus("red", e.message, false);
    } finally {
      toggleLoading("execute", false);
    }
  }

  async function generateManim() {
    if (!els.manimPrompt.value.trim())
      return showStatus("red", "Please enter a prompt", false);
    toggleLoading("generate", true);
    showStatus("indigo", "Generating Manim code...", false);

    // Add user message to chat interface immediately
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
        // Refresh the editor to update display
        els.codeEditor.refresh();

        // Add assistant response to chat
        addChatMessage(data.code, "assistant");

        // Clear the input field
        els.manimPrompt.value = "";
      } else throw new Error(data.error || "Failed to generate Manim code");
      showStatus("green", "Code generated successfully!");
    } catch (e) {
      showStatus("red", e.message, false);
    } finally {
      toggleLoading("generate", false);
    }
  }

  // Event listeners
  els.executeButton.addEventListener("click", executeManim);
  els.generateButton.addEventListener("click", generateManim);
  els.manimPrompt.addEventListener("keypress", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      generateManim();
    }
  });
  els.clearChatButton.addEventListener("click", clearChatHistory);

  // Load chat history on page load
  fetchChatHistory();
});
