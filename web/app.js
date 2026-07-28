const cases = [
  {
    id: "case_1_return_policy",
    label: "Case 1",
    title: "Return policy",
    query: "What is your return policy?",
    baseline: {
      status: "direct_answer",
      missing: "None",
      answer: "You can return eligible products within 7 days with the receipt."
    },
    agent: {
      status: "final_answer",
      toolPath: "None",
      answer: "You can return eligible products within 7 days with the receipt.",
      trace: [{ type: "llm", step: 1, content: "Final Answer: You can return eligible products within 7 days with the receipt." }]
    }
  },
  {
    id: "case_2_working_hours",
    label: "Case 2",
    title: "Working hours",
    query: "What are your working hours?",
    baseline: {
      status: "direct_answer",
      missing: "None",
      answer: "Our demo store works from 8:00 to 21:00 every day."
    },
    agent: {
      status: "final_answer",
      toolPath: "None",
      answer: "Our demo store works from 8:00 to 21:00 every day.",
      trace: [{ type: "llm", step: 1, content: "Final Answer: Our demo store works from 8:00 to 21:00 every day." }]
    }
  },
  {
    id: "case_3_iphone_winner_hanoi",
    label: "Case 3",
    title: "2 iPhones + WINNER + Hanoi",
    query: "I want to buy 2 iPhones using code 'WINNER' and ship to Hanoi. The package weight is 0.8 kg. Total?",
    baseline: {
      status: "safe_fallback",
      missing: "stock_and_price, coupon_validity, shipping_fee, final_total",
      answer: "I cannot calculate a grounded total without stock, price, coupon, and shipping evidence."
    },
    agent: {
      status: "final_answer",
      toolPath: "check_stock -> get_discount -> calc_shipping",
      answer: "Total = (25,000,000 x 2) x 0.9 + 38,000 = 45,038,000 VND.",
      trace: [
        { type: "llm", step: 1, content: 'Thought: Need stock and price.\nAction: check_stock({"item_name": "iPhone"})' },
        { type: "tool", step: 1, tool: "check_stock", observation: { ok: true, item_name: "iPhone", price: 25000000, stock: 15, weight_kg: 0.4, status: "in_stock" } },
        { type: "llm", step: 2, content: 'Thought: Need coupon evidence.\nAction: get_discount({"coupon_code": "WINNER"})' },
        { type: "tool", step: 2, tool: "get_discount", observation: { ok: true, coupon_code: "WINNER", valid: true, discount_percent: 10 } },
        { type: "llm", step: 3, content: 'Thought: Need shipping fee.\nAction: calc_shipping({"weight": 0.8, "destination": "Hanoi"})' },
        { type: "tool", step: 3, tool: "calc_shipping", observation: { ok: true, destination: "Hanoi", weight: 0.8, shipping_cost: 38000, estimated_days: 1 } },
        { type: "llm", step: 4, content: "Final Answer: Total = (25,000,000 x 2) x 0.9 + 38,000 = 45,038,000 VND." }
      ]
    }
  },
  {
    id: "case_4_macbook_out_of_stock",
    label: "Case 4",
    title: "MacBook out of stock",
    query: "Can I buy 1 MacBook and ship to Saigon? How much?",
    baseline: {
      status: "safe_fallback",
      missing: "stock_and_price, shipping_fee, final_total",
      answer: "I cannot verify MacBook stock or a grounded total without catalog and shipping tools."
    },
    agent: {
      status: "final_answer",
      toolPath: "check_stock",
      answer: "MacBook is out of stock, so I cannot claim the purchase can be completed.",
      trace: [
        { type: "llm", step: 1, content: 'Thought: Need stock before pricing checkout.\nAction: check_stock({"item_name": "MacBook"})' },
        { type: "tool", step: 1, tool: "check_stock", observation: { ok: true, item_name: "MacBook", price: 35000000, stock: 0, weight_kg: 2.0, status: "out_of_stock" } },
        { type: "llm", step: 2, content: "Final Answer: MacBook is out of stock, so I cannot claim the purchase can be completed." }
      ]
    }
  },
  {
    id: "case_5_ipad_legacy_saigon",
    label: "Case 5",
    title: "iPad + expired LEGACY",
    query: "I want to buy 1 iPad using code 'LEGACY' and ship to Saigon. The package weight is 0.5 kg. How much?",
    baseline: {
      status: "safe_fallback",
      missing: "stock_and_price, coupon_validity, shipping_fee, final_total",
      answer: "I cannot calculate a grounded total without checking price, coupon validity, and shipping."
    },
    agent: {
      status: "final_answer",
      toolPath: "check_stock -> get_discount -> calc_shipping",
      answer: "LEGACY is expired, so no discount applies. Total = 18,000,000 + 45,000 = 18,045,000 VND.",
      trace: [
        { type: "llm", step: 1, content: 'Thought: Need item stock and price.\nAction: check_stock({"item_name": "iPad"})' },
        { type: "tool", step: 1, tool: "check_stock", observation: { ok: true, item_name: "iPad", price: 18000000, stock: 8, weight_kg: 0.5, status: "in_stock" } },
        { type: "llm", step: 2, content: 'Thought: Need coupon validity.\nAction: get_discount({"coupon_code": "LEGACY"})' },
        { type: "tool", step: 2, tool: "get_discount", observation: { ok: false, error: "coupon_expired", coupon_code: "LEGACY", valid: false, discount_percent: 0 } },
        { type: "llm", step: 3, content: 'Thought: Coupon is expired; need shipping before final total.\nAction: calc_shipping({"weight": 0.5, "destination": "Saigon"})' },
        { type: "tool", step: 3, tool: "calc_shipping", observation: { ok: true, destination: "Saigon", weight: 0.5, shipping_cost: 45000, estimated_days: 2 } },
        { type: "llm", step: 4, content: "Final Answer: LEGACY is expired, so no discount applies. Total = 18,000,000 + 45,000 = 18,045,000 VND." }
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
