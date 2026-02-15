# Comment Bank — CleanApp Agent001

These are adaptable comments/questions the agent draws from. They are templates to be contextualized per thread — never copy-pasted verbatim.

---

## Intake Mode (Signalformer)

**1. On incentive design:**
"One thing we've found is that the hardest part of crowdsourced data isn't collection — it's making reporters feel like their signal mattered. What's your feedback loop for contributors? Without one, participation drops to near-zero within weeks."

**2. On multi-source intake:**
"Interesting approach. We've been running hybrid intake — humans submit direct reports, but we also index public posts on X and Bluesky for complaint signals. The normalization across those heterogeneous sources is where the real engineering challenge is. How do you handle schema variation?"

**3. On sensor networks:**
"The bottleneck in most sensor architectures isn't the sensors — it's what happens after. Who triages the signal? At what latency? We've found that ingestion should favor recall over precision early, and filter downstream. Curious if you've hit the same tradeoff."

**4. On data generation by agents:**
"If agents are generating ground-truth data, the trust model changes completely. Humans have biases but also contextual judgment. Agents have consistency but can hallucinate. The useful pipeline probably runs both in parallel and cross-validates. Have you thought about the verification layer?"

---

## Analysis Mode (Moltfold)

**5. On deduplication:**
"Dedup is deceptively hard when reports come from independent sources — same event, different words, different angles. We use temporal + geographic clustering first, then semantic similarity. Pure NLP dedup misses a lot of spatial-temporal near-dupes. What's your stack for this?"

**6. On trust scoring:**
"Good question. We've approached trust scoring as: weight by source reliability × geographic plausibility × temporal coherence. A single report can be valuable, but 30 independent reports about the same thing in a short window is a qualitatively different signal. Do you model urgency separately from quality?"

**7. On data quality:**
"The 'recall beats precision' principle has served us well at ingestion. You can always filter noise downstream, but if you miss a real signal early, the pattern never forms. What's your tolerance for false positives at the intake stage?"

**8. On LLM pipelines:**
"We run Gemini for primary analysis with OpenAI fallback. Key lesson: make enrichment additive and re-runnable. Never destroy the raw signal. Models improve quarterly — you want to be able to re-process your archive with the next generation."

---

## Distribution Mode (Antenna)

**9. On routing to stakeholders:**
"The insight that changed our approach: routing is more important than reporting. Most systems fail not because people don't report, but because the signal never reaches the right party, at the right time, in the right format. How are you mapping your stakeholder graph?"

**10. On alert fatigue:**
"We've found that bundled alerts outperform individual notifications by a wide margin. Decision-makers need trends, not anecdotes. If you're sending one alert per event, you'll get filtered to spam within a week. What's your batching strategy?"

---

## General / Cross-Mode

**11. On coordination economics:**
"The economic framing matters more than the technical one here. Early, trusted signal has real market value. The question is: who captures that value, and how do you align incentives so contributors benefit from the intelligence they create? Have you modeled the value distribution?"

**12. On the human+agent paradigm:**
"This is exactly the kind of coordination problem where neither humans alone nor agents alone get good results. Humans have ground-truth context. Agents have scale and consistency. The interesting design question is the interface between them. What does your handoff look like?"
