"""Central repository for all LLM prompts used by agents and orchestrators."""

QUESTION_PROMPT_TEMPLATE = """
You are an insightful analyst tasked with generating probing questions about the provided document. Analyze the following text content carefully. Based *only* on the information presented in this document, generate a list of {num_questions} specific and relevant questions that explore the key topics, data points, claims, or potential ambiguities within the text. The questions should encourage deeper understanding or critical evaluation of the document's content.

Avoid generic questions. Focus on questions that can, in principle, be answered using the information *within* the document itself (even if the answer isn't explicitly stated, the question should pertain directly to the document's content).

Format the output as a numbered list of questions, each on a new line.

--- BEGIN DOCUMENT CONTENT ---

{document_content}

--- END DOCUMENT CONTENT ---

Generated Questions:
1.
"""

ANSWER_PROMPT_TEMPLATE = """
You are acting as a senior financial analyst. Your task is to answer questions based *only* on the provided financial report content below, which pertains to a listed company. Do not use any external knowledge, financial assumptions, or information you might possess outside of this specific report. If the answer cannot be found within the text provided, please state clearly that the information is not available in the report.

--- BEGIN REPORT CONTENT ---

{report_content}

--- END REPORT CONTENT ---

Based strictly and solely on the report content provided above, please answer the following question:

Question: {user_query}

Answer:
"""

# Orchestrator V1 Prompts
SATISFACTION_PROMPT_TEMPLATE = """
You are an evaluation agent. Your task is to assess if the provided 'Answer' adequately and completely addresses the 'Original Question'. Do not use external knowledge. Base your assessment *only* on the text provided in the 'Answer'.

Original Question:
{question}

Answer:
{answer}

Is the Answer satisfactory in addressing the Original Question?
Respond with either "Satisfied" or "Unsatisfied".
Briefly explain the reason for your assessment (why it is satisfied or unsatisfied) based *only* on the question and answer text.

Assessment: [Satisfied/Unsatisfied]
Reason: [Brief explanation]
"""

FOLLOW_UP_PROMPT_TEMPLATE = """
You are a question refinement agent. You received an 'Original Question' and an 'Unsatisfactory Answer' that failed to fully address the question.
Your task is to generate a *single, specific* follow-up question that directly targets the missing information or inadequacy in the 'Unsatisfactory Answer'. The goal is to guide the next response towards fully answering the 'Original Question'.

Original Question:
{question}

Unsatisfactory Answer:
{answer}

Generate a follow-up question to elicit the missing information needed to satisfy the Original Question.

Follow-up Question:
"""

# Orchestrator V2 Prompts
DEBATE_SYNTHESIS_PROMPT_TEMPLATE = """
You are a neutral debate moderator and synthesizer.
Your task is to analyze multiple answers provided by different agents to the same question and synthesize a single, comprehensive, and objective final answer.

The original question was:
"{question}"

Here are the answers provided by {len_answers} different agents:

{answers_str}

--- Analysis Task ---
1.  Identify the key points of agreement and disagreement among the answers.
2.  Evaluate the evidence or reasoning presented in each answer, if applicable (note: the answers were based solely on potentially different source documents).
3.  Synthesize these perspectives into a single, final answer that best addresses the original question based on the collective information provided.
4.  If the answers conflict significantly or some seem unreliable (e.g., contain error messages), acknowledge this in your synthesis.
5.  Ensure the final answer is objective and does not introduce external information not present in the provided answers.

--- Final Synthesized Answer ---
"""

# Orchestrator V3 Prompts
DEBATE_PARTICIPATION_PROMPT_TEMPLATE = """
You are an expert financial analyst participating in a multi-round debate regarding the following question. You must base your response *only* on the provided 'Your Document Context' and the 'Debate History So Far'. Do not use external knowledge.

Original Question:
"{question}"

--- Your Document Context ---
{document_context}
--- End Document Context ---

--- Debate History So Far ---
{debate_history}
--- End Debate History ---

Your Task for this Round ({current_round}):
Analyze the 'Original Question', 'Your Document Context', and the 'Debate History So Far'.
Provide a concise and informative contribution to the debate for the current round. You can:
- Reiterate or refine your previous points if necessary, citing your document.
- Address points made by other agents in the history, agreeing or disagreeing with justification from your document.
- Provide new insights based on your document that are relevant to the question and the ongoing discussion.
- If your document cannot provide further relevant information, state that clearly.

Keep your response focused on directly contributing to answering the 'Original Question' based *only* on your provided context and the prior debate turns.

Your Response for Round {current_round}:
"""

FINAL_SYNTHESIS_PROMPT_TEMPLATE_V3 = """
You are a neutral and objective summarizer. Your task is to synthesize a final answer to the 'Original Question' based *only* on the provided 'Full Debate History'.

The 'Full Debate History' contains multiple rounds of discussion where different agents provided answers and potentially debated points based on their respective source documents.

Original Question:
\"{question}\"

--- Full Debate History ---
{debate_history}
--- End Full Debate History ---

Your Synthesis Task:
1. Carefully review the entire 'Full Debate History', noting the progression of the discussion, points of agreement, disagreement, and refinement across rounds.
2. Synthesize a single, comprehensive final answer that accurately reflects the collective information presented throughout the debate.
3. Prioritize information from later rounds if it clearly refines or corrects earlier points, but ensure the final answer considers the entire context.
4. If significant unresolved disagreements remain based *only* on the history, acknowledge them objectively.
5. Do not introduce any external information or opinions not present in the 'Full Debate History'.
6. Ensure the final answer directly addresses the 'Original Question'.

--- Final Synthesized Answer ---
""" 