const cases = [
  {
    id: "case_1_return_policy",
    label: "Case 1",
    title: "Chính sách đổi trả",
    query: "Chính sách đổi trả là gì?",
    baseline: {
      status: "direct_answer",
      missing: "Không thiếu",
      answer: "Bạn có thể đổi trả sản phẩm đủ điều kiện trong 7 ngày nếu còn hóa đơn."
    },
    agent: {
      status: "final_answer",
      toolPath: "Không gọi Tool",
      answer: "Bạn có thể đổi trả sản phẩm đủ điều kiện trong 7 ngày nếu còn hóa đơn.",
      trace: [{ type: "llm", step: 1, content: "Final Answer: Bạn có thể đổi trả sản phẩm đủ điều kiện trong 7 ngày nếu còn hóa đơn." }]
    }
  },
  {
    id: "case_2_working_hours",
    label: "Case 2",
    title: "Giờ làm việc",
    query: "Cửa hàng làm việc lúc nào?",
    baseline: {
      status: "direct_answer",
      missing: "Không thiếu",
      answer: "Cửa hàng demo làm việc từ 8:00 đến 21:00 hằng ngày."
    },
    agent: {
      status: "final_answer",
      toolPath: "Không gọi Tool",
      answer: "Cửa hàng demo làm việc từ 8:00 đến 21:00 hằng ngày.",
      trace: [{ type: "llm", step: 1, content: "Final Answer: Cửa hàng demo làm việc từ 8:00 đến 21:00 hằng ngày." }]
    }
  },
  {
    id: "case_3_iphone_winner_hanoi",
    label: "Case 3",
    title: "2 iPhone + WINNER + Hanoi",
    query: "Tôi muốn mua 2 iPhone, dùng mã WINNER và giao tới Hanoi. Package weight là 0.8 kg. Tổng tiền là bao nhiêu?",
    baseline: {
      status: "safe_fallback",
      missing: "stock_and_price, coupon_validity, shipping_fee, final_total",
      answer: "Tôi không thể tính tổng tiền có căn cứ nếu chưa có bằng chứng về tồn kho, giá, coupon và shipping."
    },
    agent: {
      status: "final_answer",
      toolPath: "check_stock -> get_discount -> calc_shipping -> calc_total",
      answer: "Tổng tiền = (25,000,000 x 2) x 0.9 + 38,000 = 45,038,000 VND.",
      trace: [
        { type: "llm", step: 1, content: 'Thought: Cần kiểm tra tồn kho và giá.\nAction: check_stock({"item_name": "iPhone"})' },
        { type: "tool", step: 1, tool: "check_stock", observation: { ok: true, item_name: "iPhone", price: 25000000, stock: 15, weight_kg: 0.4, status: "in_stock" } },
        { type: "llm", step: 2, content: 'Thought: Cần bằng chứng coupon.\nAction: get_discount({"coupon_code": "WINNER"})' },
        { type: "tool", step: 2, tool: "get_discount", observation: { ok: true, coupon_code: "WINNER", valid: true, discount_percent: 10 } },
        { type: "llm", step: 3, content: 'Thought: Cần tính phí shipping.\nAction: calc_shipping({"weight": 0.8, "destination": "Hanoi"})' },
        { type: "tool", step: 3, tool: "calc_shipping", observation: { ok: true, destination: "Hanoi", weight: 0.8, shipping_cost: 38000, estimated_days: 1 } },
        { type: "llm", step: 4, content: 'Thought: Cần tính total có cấu trúc.\nAction: calc_total({"item_quantity": 2, "price_per_item": 25000000, "discount_percent": 10, "shipping_cost": 38000})' },
        { type: "tool", step: 4, tool: "calc_total", observation: { ok: true, subtotal: 50000000, discount_amount: 5000000, shipping_cost: 38000, total: 45038000, currency: "VND" } },
        { type: "llm", step: 5, content: "Final Answer: Tổng tiền = 45,038,000 VND." }
      ]
    }
  },
  {
    id: "case_4_macbook_out_of_stock",
    label: "Case 4",
    title: "MacBook hết hàng",
    query: "Tôi có thể mua 1 MacBook và ship tới Saigon không? Giá bao nhiêu?",
    baseline: {
      status: "safe_fallback",
      missing: "stock_and_price, shipping_fee, final_total",
      answer: "Tôi không thể xác minh tồn kho MacBook hoặc tổng tiền nếu không có catalog và shipping Tool."
    },
    agent: {
      status: "final_answer",
      toolPath: "check_stock",
      answer: "MacBook đang hết hàng, nên tôi không thể khẳng định đơn mua có thể hoàn tất.",
      trace: [
        { type: "llm", step: 1, content: 'Thought: Cần kiểm tra tồn kho trước khi tính checkout.\nAction: check_stock({"item_name": "MacBook"})' },
        { type: "tool", step: 1, tool: "check_stock", observation: { ok: true, item_name: "MacBook", price: 35000000, stock: 0, weight_kg: 2.0, status: "out_of_stock" } },
        { type: "llm", step: 2, content: "Final Answer: MacBook đang hết hàng, nên tôi không thể khẳng định đơn mua có thể hoàn tất." }
      ]
    }
  },
  {
    id: "case_5_ipad_legacy_saigon",
    label: "Case 5",
    title: "iPad + LEGACY hết hạn",
    query: "Tôi muốn mua 1 iPad, dùng mã LEGACY và ship tới Saigon. Package weight là 0.5 kg. Bao nhiêu tiền?",
    baseline: {
      status: "safe_fallback",
      missing: "stock_and_price, coupon_validity, shipping_fee, final_total",
      answer: "Tôi không thể tính tổng tiền có căn cứ nếu chưa kiểm tra giá, coupon validity và shipping."
    },
    agent: {
      status: "final_answer",
      toolPath: "check_stock -> get_discount -> calc_shipping -> calc_total",
      answer: "LEGACY đã hết hạn nên không áp dụng giảm giá. Tổng tiền = 18,000,000 + 45,000 = 18,045,000 VND.",
      trace: [
        { type: "llm", step: 1, content: 'Thought: Cần tồn kho và giá sản phẩm.\nAction: check_stock({"item_name": "iPad"})' },
        { type: "tool", step: 1, tool: "check_stock", observation: { ok: true, item_name: "iPad", price: 18000000, stock: 8, weight_kg: 0.5, status: "in_stock" } },
        { type: "llm", step: 2, content: 'Thought: Cần kiểm tra coupon validity.\nAction: get_discount({"coupon_code": "LEGACY"})' },
        { type: "tool", step: 2, tool: "get_discount", observation: { ok: false, error: "coupon_expired", coupon_code: "LEGACY", valid: false, discount_percent: 0 } },
        { type: "llm", step: 3, content: 'Thought: Coupon hết hạn; cần shipping trước khi tính tổng.\nAction: calc_shipping({"weight": 0.5, "destination": "Saigon"})' },
        { type: "tool", step: 3, tool: "calc_shipping", observation: { ok: true, destination: "Saigon", weight: 0.5, shipping_cost: 45000, estimated_days: 2 } },
        { type: "llm", step: 4, content: 'Thought: Cần tính total không giảm giá.\nAction: calc_total({"item_quantity": 1, "price_per_item": 18000000, "discount_percent": 0, "shipping_cost": 45000})' },
        { type: "tool", step: 4, tool: "calc_total", observation: { ok: true, subtotal: 18000000, discount_amount: 0, shipping_cost: 45000, total: 18045000, currency: "VND" } },
        { type: "llm", step: 5, content: "Final Answer: LEGACY đã hết hạn nên không áp dụng giảm giá. Tổng tiền = 18,045,000 VND." }
      ]
    }
  }
];

const buttonWrap = document.querySelector("#caseButtons");
const baselineAnswer = document.querySelector("#baselineAnswer");
const baselineStatus = document.querySelector("#baselineStatus");
const baselineEvidence = document.querySelector("#baselineEvidence");
const agentAnswer = document.querySelector("#agentAnswer");
const agentStatus = document.querySelector("#agentStatus");
const toolPath = document.querySelector("#toolPath");
const traceList = document.querySelector("#traceList");
const liveQuery = document.querySelector("#liveQuery");
const askAgent = document.querySelector("#askAgent");
const askBaseline = document.querySelector("#askBaseline");
const liveStatus = document.querySelector("#liveStatus");
const liveResult = document.querySelector("#liveResult");
const liveGraph = document.querySelector("#liveGraph");
const providerSelect = document.querySelector("#providerSelect");
const activeProvider = document.querySelector("#activeProvider");
const activeModel = document.querySelector("#activeModel");
const activeStatus = document.querySelector("#activeStatus");
const activeTools = document.querySelector("#activeTools");
const providerStatus = document.querySelector("#providerStatus");
const graphDetailTitle = document.querySelector("#graphDetailTitle");
const graphDetailContent = document.querySelector("#graphDetailContent");
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

function formatTrace(step) {
  if (step.type === "tool") {
    return {
      label: `Step ${step.step} · Tool`,
      title: step.tool,
      body: JSON.stringify(step.observation, null, 2)
    };
  }

  return {
    label: `Step ${step.step} · LLM`,
    title: step.content.startsWith("Final Answer") ? "Final Answer" : "Thought + Action",
    body: step.content
  };
}

function renderCase(selected) {
  document.querySelectorAll(".case-buttons button").forEach((button) => {
    button.classList.toggle("active", button.dataset.caseId === selected.id);
  });

  baselineAnswer.textContent = selected.baseline.answer;
  baselineStatus.textContent = selected.baseline.status;
  baselineEvidence.textContent = selected.baseline.missing;
  agentAnswer.textContent = selected.agent.answer;
  agentStatus.textContent = selected.agent.status;
  toolPath.textContent = selected.agent.toolPath;

  traceList.innerHTML = "";
  selected.agent.trace.forEach((step) => {
    const item = formatTrace(step);
    const node = document.createElement("article");
    node.className = `trace-step ${step.type}`;
    node.innerHTML = `<div><strong>${item.label}</strong><span>${item.title}</span></div><pre>${item.body}</pre>`;
    traceList.appendChild(node);
  });
}

cases.forEach((item, index) => {
  const button = document.createElement("button");
  button.type = "button";
  button.dataset.caseId = item.id;
  button.innerHTML = `<span>${item.label}</span><br><small>${item.title}</small>`;
  button.addEventListener("click", () => renderCase(item));
  buttonWrap.appendChild(button);
  if (index === 2) renderCase(item);
});

function nodeInfo(event) {
  if (event.type === "start") {
    return {
      kind: "start",
      title: "Start",
      meta: event.provider,
      summary: `${event.mode} · ${event.model}`,
      detail: JSON.stringify(event, null, 2)
    };
  }
  if (event.type === "scope") {
    const inScope = event.scope?.in_scope;
    return {
      kind: inScope ? "tool" : "warning",
      title: inScope ? "Scope ok" : "Scope gate",
      meta: inScope ? "in scope" : "out of scope",
      summary: inScope ? "Question matches demo scope." : "Stopped before LLM to avoid hallucination.",
      detail: JSON.stringify(event.scope, null, 2)
    };
  }
  if (event.type === "llm") {
    const isFinal = event.content?.startsWith("Final Answer");
    return {
      kind: isFinal ? "final" : "llm",
      title: isFinal ? "Final draft" : "LLM",
      meta: `${event.latency_ms || 0}ms`,
      summary: isFinal ? "Model proposes the final answer." : "Model chooses the next Thought/Action.",
      detail: event.content || ""
    };
  }
  if (event.type === "tool") {
    const ok = event.observation?.ok === false ? "error" : "ok";
    return {
      kind: ok === "ok" ? "tool" : "warning",
      title: event.tool,
      meta: ok,
      summary: ok === "ok" ? "Tool returned a grounded observation." : event.observation?.error || "Tool guardrail.",
      detail: JSON.stringify({ arguments: event.arguments, observation: event.observation }, null, 2)
    };
  }
  if (event.type === "observation") {
    return {
      kind: "warning",
      title: event.observation?.error || "Observation",
      meta: "guardrail",
      summary: event.observation?.message || "Application injected a guardrail observation.",
      detail: JSON.stringify(event.observation, null, 2)
    };
  }
  if (event.type === "result") {
    return {
      kind: "final",
      title: "Done",
      meta: event.result?.status || event.result?.classification || "result",
      summary: event.result?.answer || "Request completed.",
      detail: JSON.stringify(event.result, null, 2)
    };
  }
  return { kind: "warning", title: "Error", meta: event.error || "", detail: event.message || JSON.stringify(event) };
}

function appendGraphNode(event) {
  const item = nodeInfo(event);
  const node = document.createElement("article");
  node.className = `graph-node ${item.kind}`;
  node.tabIndex = 0;
  const stepNumber = liveGraph.children.length + 1;
  node.innerHTML = `
    <b>${stepNumber}</b>
    <div>
      <span>${item.title}</span>
      <p>${item.summary || ""}</p>
    </div>
    <strong>${item.meta}</strong>
  `;
  const showDetail = () => {
    graphDetailTitle.textContent = `${item.title} · ${item.meta}`;
    graphDetailContent.textContent = item.detail || "Không có chi tiết.";
  };
  node.addEventListener("mouseenter", showDetail);
  node.addEventListener("focus", showDetail);
  node.addEventListener("click", showDetail);
  liveGraph.appendChild(node);
  node.scrollIntoView({ behavior: "smooth", block: "nearest" });
  showDetail();
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
    providerStatus.textContent = event.provider === "groq" ? "Groq API" : "Ollama local";
    return;
  }
  if (event.type === "tool") {
    const current = activeTools.textContent === "-" ? [] : activeTools.textContent.split(" → ");
    current.push(event.tool);
    activeTools.textContent = current.join(" → ");
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
    liveResult.textContent = event.result?.answer || "Không có answer.";
  }
}

async function runLive(mode) {
  const query = liveQuery.value.trim();
  if (!query) return;

  liveStatus.textContent = mode === "baseline" ? "Đang gọi Baseline..." : "Đang gọi Agent + Tool...";
  liveResult.textContent = "Đang chạy...";
  liveGraph.innerHTML = "";
  resetMetrics();
  graphDetailTitle.textContent = "Chi tiết node";
  graphDetailContent.textContent = "Graph đang chạy...";
  activeStatus.textContent = "running";
  activeTools.textContent = "-";
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
        appendGraphNode(event);
        updateSummary(event);
        updateMetrics(event);
        if (event.type === "error") throw new Error(event.message || event.error);
      }
    }
    liveStatus.textContent = "Hoàn tất";
  } catch (error) {
    liveStatus.textContent = "Lỗi live request";
    liveResult.textContent = error.message;
    appendGraphNode({ type: "error", error: "request_failed", message: error.message });
  } finally {
    askAgent.disabled = false;
    askBaseline.disabled = false;
  }
}

askAgent.addEventListener("click", () => runLive("agent"));
askBaseline.addEventListener("click", () => runLive("baseline"));

async function loadHealth() {
  try {
    const response = await fetch("/api/health");
    const payload = await response.json();
    activeModel.textContent = payload.model || activeModel.textContent;
    activeProvider.textContent = payload.provider || activeProvider.textContent;
  } catch {
    providerStatus.textContent = "Backend offline";
  }
}

loadHealth();
renderMetrics();
