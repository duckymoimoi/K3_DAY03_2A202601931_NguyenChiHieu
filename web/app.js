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
      toolPath: "check_stock -> get_discount -> calc_shipping",
      answer: "Tổng tiền = (25,000,000 x 2) x 0.9 + 38,000 = 45,038,000 VND.",
      trace: [
        { type: "llm", step: 1, content: 'Thought: Cần kiểm tra tồn kho và giá.\nAction: check_stock({"item_name": "iPhone"})' },
        { type: "tool", step: 1, tool: "check_stock", observation: { ok: true, item_name: "iPhone", price: 25000000, stock: 15, weight_kg: 0.4, status: "in_stock" } },
        { type: "llm", step: 2, content: 'Thought: Cần bằng chứng coupon.\nAction: get_discount({"coupon_code": "WINNER"})' },
        { type: "tool", step: 2, tool: "get_discount", observation: { ok: true, coupon_code: "WINNER", valid: true, discount_percent: 10 } },
        { type: "llm", step: 3, content: 'Thought: Cần tính phí shipping.\nAction: calc_shipping({"weight": 0.8, "destination": "Hanoi"})' },
        { type: "tool", step: 3, tool: "calc_shipping", observation: { ok: true, destination: "Hanoi", weight: 0.8, shipping_cost: 38000, estimated_days: 1 } },
        { type: "llm", step: 4, content: "Final Answer: Tổng tiền = (25,000,000 x 2) x 0.9 + 38,000 = 45,038,000 VND." }
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
      toolPath: "check_stock -> get_discount -> calc_shipping",
      answer: "LEGACY đã hết hạn nên không áp dụng giảm giá. Tổng tiền = 18,000,000 + 45,000 = 18,045,000 VND.",
      trace: [
        { type: "llm", step: 1, content: 'Thought: Cần tồn kho và giá sản phẩm.\nAction: check_stock({"item_name": "iPad"})' },
        { type: "tool", step: 1, tool: "check_stock", observation: { ok: true, item_name: "iPad", price: 18000000, stock: 8, weight_kg: 0.5, status: "in_stock" } },
        { type: "llm", step: 2, content: 'Thought: Cần kiểm tra coupon validity.\nAction: get_discount({"coupon_code": "LEGACY"})' },
        { type: "tool", step: 2, tool: "get_discount", observation: { ok: false, error: "coupon_expired", coupon_code: "LEGACY", valid: false, discount_percent: 0 } },
        { type: "llm", step: 3, content: 'Thought: Coupon hết hạn; cần shipping trước khi tính tổng.\nAction: calc_shipping({"weight": 0.5, "destination": "Saigon"})' },
        { type: "tool", step: 3, tool: "calc_shipping", observation: { ok: true, destination: "Saigon", weight: 0.5, shipping_cost: 45000, estimated_days: 2 } },
        { type: "llm", step: 4, content: "Final Answer: LEGACY đã hết hạn nên không áp dụng giảm giá. Tổng tiền = 18,000,000 + 45,000 = 18,045,000 VND." }
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
