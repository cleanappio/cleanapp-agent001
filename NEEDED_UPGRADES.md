# CleanApp Agent Upgrade Roadmap

This document outlines planned improvements to make the agent smarter, more autonomous, and self-learning.

## 1. Recursive Self-Improvement (Reinforcement Learning Lite)

**Goal**: To allow the agent to automatically double down on successful strategies and prune failures without manual intervention.

### Implementation Plan

#### A. Memory Upgrade (`src/memory.py`)
Add an `outcomes` table to track the results of our engagements.
```python
# PROTOCODE: Schema Update
cursor.execute("""
    CREATE TABLE outcomes (
        post_id TEXT PRIMARY KEY,
        engagement_id INTEGER REFERENCES engagements(id),
        reply_count INTEGER DEFAULT 0,
        upvote_count INTEGER DEFAULT 0, 
        sentiment_score FLOAT,  # calculated from replies
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
""")
```

#### B. Feedback Loop (`src/learning.py`)
Create a new module that runs periodically (e.g., daily) to analyze performance.
```python
# PROTOCODE: Learning Loop
def analyze_performance(memory):
    # Identify top performing topics/queries based on replies/upvotes
    successful_threads = memory.get_high_engagement_threads()
    
    # Extract keywords from success cases
    new_keywords = extract_keywords(successful_threads)
    
    # Identify failures (skipped or ignored threads)
    failed_queries = memory.get_zero_engagement_queries()
    
    return {
        "promote": new_keywords,
        "demote": failed_queries
    }

def update_agent_config(analysis):
    # Dynamically update SEARCH_QUERIES
    current_queries = load_queries()
    # Remove lowest performing 10%
    # Add new derived keywords from success cases
    save_queries(optimized_queries)
```

#### C. Testing & Safety
- **Sandbox Mode**: Run the learning loop in "suggestion mode" first, where it proposes changes to a PR rather than auto-applying them.
- **Drift Protection**: Hard-code core mission queries (like "trashformer") so the agent doesn't drift into high-engagement but irrelevant topics (like "cats" or "crypto").

## 2. Conversation Continuity
- **Goal**: Allow the agent to reply to replies.
- **Mechanism**: Poll `get_notifications()` and use a conversational prompt to continue legitimate threads while detecting and ignoring trolls.

## 3. Dynamic Persona
- **Goal**: Adapt tone based on the submolt.
- **Mechanism**: 
    - In `s/engineering`: Use technical, terse language.
    - In `s/introductions`: Use welcoming, emoji-friendly language.
    - Detect submolt vibe via LLM before generating response.
