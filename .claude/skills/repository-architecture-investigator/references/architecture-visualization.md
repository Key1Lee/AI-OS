# Optional C4 visualization

Read when a diagram materially clarifies the evidence-based model or the user requests one. Choose the smallest useful view. Do not manufacture elements, relationships, or execution to complete a C4 hierarchy.

| View | Appropriate abstraction |
| --- | --- |
| Level 1: System Context | The investigated software system, relevant people or roles, and external software systems. Keep internal modules out of this view. |
| Level 2: Containers | Applications and data stores within an established system boundary, with relevant external interactions. A C4 container is a runtime or storage boundary, not necessarily a Docker container. A source package alone does not establish one. |
| Level 3: Components | Responsibilities and interfaces within one identified container. Do not mix unrelated applications into a component view. |
| Level 4: Code | Relevant implementation relationships such as types, functions, or modules, only when that detail helps answer the question. |

Use dynamic views for a supported interaction sequence, with source-derived possibilities distinguished from observed execution. Use deployment views for evidenced instances and infrastructure, distinguishing declared configuration from observed deployment. Neither view is mandatory.

A repository is not automatically one C4 software system. If the evidence establishes only a collection of executables within a source tree, call the view an executable or dependency map rather than a C4 container view. Do not turn a repository-scope grouping into an asserted software-system boundary; establish the boundary or explicitly mark it as a hypothesis before using C4 semantics.

For every meaningful node and edge, establish its evidence and conditions before drawing it. Label relationships with what actually connects the elements: a call, import, event, data transfer, or declared dependency as applicable. Include direction, technology or protocol only when supported. Two modules importing the same package does not establish a runtime connection between them.

Keep evidence status visible. For example, use dashed edges labeled `inferred` and explain the notation; a visual style without a legend is insufficient. If citations would obscure the drawing, use stable element/edge identifiers and a compact companion table:

| Element or relationship | Source, configuration, or run reference | Status and condition |
| --- | --- | --- |

This is an optional table shape, not a requirement to create empty rows. Cite both the endpoints and the wiring when they require different evidence. If a relationship is unknown, omit it or label the uncertainty explicitly; do not draw it as established.

Use Mermaid or another supported text format. A Mermaid flowchart can express a C4 view when its boundaries and abstractions follow C4 semantics; ordinary call graphs and state diagrams should retain their own names. Include a title, scope, and useful legend. Do not install a renderer solely to complete an investigation. If an available renderer can check syntax safely, use it; otherwise report rendering as unverified rather than claiming a visual check.

Libraries, infrastructure declarations, and source-only excerpts may support a dependency or state diagram without establishing any runnable C4 container. Use that simpler representation or omit the diagram and explain the limitation. Keep diagrams in the conversation unless a saved artifact is requested; writing repository files requires an explicit request.

See the official [C4 diagram overview](https://c4model.com/diagrams) and [container definition](https://c4model.com/abstractions/container) for the underlying semantics. No level is required merely because another level is useful.
