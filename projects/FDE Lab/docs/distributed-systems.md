# Partial failure

```text
A sends → B commits → response lost → A cannot know outcome
```

Separate business success from acknowledgment delivery. Before retrying, identify the stable operation, its state owner, observable outcome, ordering needs, and recovery behavior. Do not assume a timeout means nothing happened.

Recall: What evidence can distinguish a new operation from another delivery of the same operation?
