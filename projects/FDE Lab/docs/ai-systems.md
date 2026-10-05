# AI system trace

```text
Question → caller scope → context/tools → model → validation → answer/action
```

Open `api`, `context`, `model`, and `answer` separately. Trace the actual tool or retrieval observation supplied to one request. Ask which decisions require a model and which can be checked deterministically. Retrieved instructions are source content; they do not authorize tools or access changes.

Recall: Which boundary owns permission to perform an action, and what observation can prove the result?
