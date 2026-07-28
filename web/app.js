const liveQuery = document.querySelector("#liveQuery");
const askAgent = document.querySelector("#askAgent");
const askBaseline = document.querySelector("#askBaseline");
const liveStatus = document.querySelector("#liveStatus");
const conversationFlow = document.querySelector("#conversationFlow");
const liveGraph = document.querySelector("#liveGraph");
const providerSelect = document.querySelector("#providerSelect");
const activeProvider = document.querySelector("#activeProvider");
const activeModel = document.querySelector("#activeModel");
const activeStatus = document.querySelector("#activeStatus");
const activeTools = document.querySelector("#activeTools");
const providerStatus = document.querySelector("#providerStatus");
const metricLlmCalls = document.querySelector("#metricLlmCalls");
const metricToolCalls = document.querySelector("#metricToolCalls");
const metricTokens = document.querySelector("#metricTokens");
const metricLatency = document.querySelector("#metricLatency");
const metricRatio = document.querySelector("#metricRatio");

let liveMetrics = {
  llmCalls: 0,
  toolCalls: 0,
  promptTokens: 0,
  completionTokens: 0,
  totalTokens: 0,
  latencyMs: 0
};

function appendMessage(role, text) {
  const message = document.createElement("article");
  message.className = `message ${role}`;

  const label = document.createElement("span");
  label.textContent = role === "user" ? "Bạn" : "Agent";

  const body = document.createElement("div");
  body.className = "message-body";
  body.textContent = text;

  message.append(label, body);
  conversationFlow.appendChild(message);
  message.scrollIntoView({ behavior: "smooth", block: "nearest" });
  return body;
}

function formatVnd(value) {
  return `${Number(value).toLocaleString("en-US")} VND`;
}

function renderResultMessage(target, result) {
  target.textContent = "";
  const display = result?.display;
  if (!display?.sections) {
    target.textContent = result?.answer || "Không có answer.";
    return;
  }

  if (display.sections.total) {
    const group = document.createElement("section");
    group.className = "answer-group total";
    group.innerHTML = "<h3>Tổng đơn hàng</h3>";
    const grid = document.createElement("div");
    grid.className = "answer-kv";
    display.sections.total.forEach((item) => {
      const row = document.createElement("div");
      row.innerHTML = `<span>${item.label}</span><strong>${item.value}</strong>`;
      grid.appendChild(row);
    });
    group.appendChild(grid);
    target.appendChild(group);
  }

  if (display.sections.products) {
    const group = document.createElement("section");
    group.className = "answer-group";
    group.innerHTML = "<h3>Sản phẩm</h3>";
    display.sections.products.forEach((product) => {
      const item = document.createElement("article");
      item.className = "answer-row";
      item.innerHTML = `
        <strong>${product.item_name}</strong>
        <span>${formatVnd(product.price)} · ${product.status === "in_stock" ? "còn hàng" : "hết hàng"}</span>
        <small>Stock: ${product.stock} · Weight: ${product.weight_kg} kg</small>
      `;
      group.appendChild(item);
    });
    target.appendChild(group);
  }

  if (display.sections.coupons) {
    const group = document.createElement("section");
    group.className = "answer-group";
    group.innerHTML = "<h3>Mã giảm giá</h3>";
    display.sections.coupons.forEach((coupon) => {
      const item = document.createElement("article");
      item.className = "answer-row compact";
      item.innerHTML = `
        <strong>${coupon.coupon_code}</strong>
        <span>Giảm ${coupon.discount_percent}%</span>
      `;
      group.appendChild(item);
    });
    target.appendChild(group);
  }

  if (display.sections.shipping) {
    const group = document.createElement("section");
    group.className = "answer-group";
    group.innerHTML = "<h3>Bảng giá ship</h3>";
    display.sections.shipping.forEach((option) => {
      const item = document.createElement("article");
      item.className = "answer-row";
      item.innerHTML = `
        <strong>${option.destination}</strong>
        <span>Base ${formatVnd(option.base_cost)} + ${formatVnd(option.per_kg)}/kg</span>
        <small>ETA: ${option.estimated_days} ngày</small>
      `;
      group.appendChild(item);
    });
    target.appendChild(group);
  }
}

function detailText(event) {
  if (event.type === "start") return JSON.stringify(event, null, 2);
  if (event.type === "scope") return JSON.stringify(event.scope, null, 2);
  if (event.type === "llm") return event.content || "";
  if (event.type === "tool") {
    return JSON.stringify({ arguments: event.arguments, observation: event.observation }, null, 2);
  }
  if (event.type === "observation") return JSON.stringify(event.observation, null, 2);
  if (event.type === "result") return JSON.stringify(event.result, null, 2);
  return event.message || JSON.stringify(event, null, 2);
}

function flowInfo(event) {
  if (event.type === "start") {
    return {
      kind: "start",
      title: "Start",
      meta: event.provider,
      summary: `${event.mode} · ${event.model}`
    };
  }
  if (event.type === "scope") {
    const inScope = event.scope?.in_scope;
    return {
      kind: inScope ? "tool" : "warning",
      title: inScope ? "Scope ok" : "Scope gate",
      meta: inScope ? "in scope" : "out of scope",
      summary: inScope ? "Câu hỏi nằm trong phạm vi demo." : "Dừng trước LLM để tránh hallucination."
    };
  }
  if (event.type === "llm") {
    const isFinal = event.content?.startsWith("Final Answer");
    return {
      kind: isFinal ? "final" : "llm",
      title: isFinal ? "Final draft" : "LLM",
      meta: `${event.latency_ms || 0} ms`,
      summary: isFinal ? "Model đề xuất câu trả lời cuối." : "Model chọn Thought/Action tiếp theo."
    };
  }
  if (event.type === "tool") {
    const ok = event.observation?.ok === false ? "error" : "ok";
    return {
      kind: ok === "ok" ? "tool" : "warning",
      title: event.tool,
      meta: ok,
      summary: ok === "ok" ? "Tool trả observation có cấu trúc." : event.observation?.error || "Tool guardrail."
    };
  }
  if (event.type === "observation") {
    return {
      kind: "warning",
      title: event.observation?.error || "Observation",
      meta: "guardrail",
      summary: event.observation?.message || "Application chèn observation để recovery."
    };
  }
  if (event.type === "result") {
    return {
      kind: "final",
      title: "Done",
      meta: event.result?.status || event.result?.classification || "result",
      summary: event.result?.answer || "Hoàn tất request."
    };
  }
  return {
    kind: "warning",
    title: "Error",
    meta: event.error || "",
    summary: event.message || "Request lỗi."
  };
}

function appendFlowStep(event) {
  const info = flowInfo(event);
  const step = document.createElement("article");
  step.className = `flow-step ${info.kind}`;

  const index = document.createElement("b");
  index.textContent = String(liveGraph.querySelectorAll(".flow-step").length + 1);

  const content = document.createElement("div");
  const heading = document.createElement("header");
  const title = document.createElement("strong");
  title.textContent = info.title;
  const meta = document.createElement("span");
  meta.textContent = info.meta;
  heading.append(title, meta);

  const summary = document.createElement("p");
  summary.textContent = info.summary;

  const detail = document.createElement("pre");
  detail.textContent = detailText(event);

  content.append(heading, summary, detail);
  step.append(index, content);
  liveGraph.appendChild(step);
  step.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function resetMetrics() {
  liveMetrics = {
    llmCalls: 0,
    toolCalls: 0,
    promptTokens: 0,
    completionTokens: 0,
    totalTokens: 0,
    latencyMs: 0
  };
  renderMetrics();
}

function renderMetrics() {
  const ratio = liveMetrics.promptTokens
    ? liveMetrics.completionTokens / liveMetrics.promptTokens
    : 0;
  metricLlmCalls.textContent = liveMetrics.llmCalls;
  metricToolCalls.textContent = liveMetrics.toolCalls;
  metricTokens.textContent = liveMetrics.totalTokens.toLocaleString("en-US");
  metricLatency.textContent = `${liveMetrics.latencyMs.toLocaleString("en-US")} ms`;
  metricRatio.textContent = ratio.toFixed(2);
}

function updateMetrics(event) {
  if (event.type === "llm") {
    const usage = event.usage || {};
    liveMetrics.llmCalls += 1;
    liveMetrics.promptTokens += usage.prompt_tokens || 0;
    liveMetrics.completionTokens += usage.completion_tokens || 0;
    liveMetrics.totalTokens += usage.total_tokens || 0;
    liveMetrics.latencyMs += event.latency_ms || 0;
    renderMetrics();
    return;
  }
  if (event.type === "tool") {
    liveMetrics.toolCalls += 1;
    renderMetrics();
  }
}

function updateSummary(event) {
  if (event.type === "start") {
    activeProvider.textContent = event.provider;
    activeModel.textContent = event.model;
    activeStatus.textContent = "running";
    activeTools.textContent = "-";
    providerStatus.textContent = event.provider === "groq" ? "Cloud API" : "Ollama local";
    return;
  }
  if (event.type === "tool") {
    const current = activeTools.textContent === "-" ? [] : activeTools.textContent.split(" -> ");
    current.push(event.tool);
    activeTools.textContent = current.join(" -> ");
    activeStatus.textContent = event.observation?.ok === false ? "guardrail" : "tool";
    return;
  }
  if (event.type === "llm") {
    activeStatus.textContent = event.content?.startsWith("Final Answer") ? "answering" : "thinking";
    return;
  }
  if (event.type === "scope") {
    activeStatus.textContent = event.scope?.in_scope ? "in_scope" : "out_of_scope";
    return;
  }
  if (event.type === "result") {
    activeStatus.textContent = event.result?.status || event.result?.classification || "done";
  }
}

async function runLive(mode) {
  const query = liveQuery.value.trim();
  if (!query) return;

  appendMessage("user", query);
  const assistantMessage = appendMessage("assistant", "Đang xử lý...");
  liveGraph.innerHTML = "";
  resetMetrics();
  activeStatus.textContent = "running";
  activeTools.textContent = "-";
  liveStatus.textContent = mode === "baseline" ? "Đang gọi Baseline..." : "Đang gọi Agent + Tool...";
  askAgent.disabled = true;
  askBaseline.disabled = true;

  try {
    const response = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode, query, provider: providerSelect.value })
    });
    if (!response.ok && !response.body) throw new Error("Live request failed");

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();
      for (const line of lines) {
        if (!line.trim()) continue;
        const event = JSON.parse(line);
        appendFlowStep(event);
        updateSummary(event);
        updateMetrics(event);
        if (event.type === "result") {
          renderResultMessage(assistantMessage, event.result);
        }
        if (event.type === "error") throw new Error(event.message || event.error);
      }
    }
    liveStatus.textContent = "Hoàn tất";
  } catch (error) {
    liveStatus.textContent = "Lỗi live request";
    assistantMessage.textContent = error.message;
    appendFlowStep({ type: "error", error: "request_failed", message: error.message });
  } finally {
    askAgent.disabled = false;
    askBaseline.disabled = false;
    liveQuery.focus();
  }
}

askAgent.addEventListener("click", () => runLive("agent"));
askBaseline.addEventListener("click", () => runLive("baseline"));
liveQuery.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
    runLive("agent");
  }
});

async function loadHealth() {
  try {
    const response = await fetch("/api/health");
    const payload = await response.json();
    activeModel.textContent = payload.model || activeModel.textContent;
    activeProvider.textContent = payload.provider || activeProvider.textContent;
    providerStatus.textContent = payload.provider || "Cloud API";
  } catch {
    providerStatus.textContent = "Backend offline";
  }
}

loadHealth();
renderMetrics();
