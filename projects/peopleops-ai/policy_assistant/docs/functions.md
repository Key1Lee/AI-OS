# Core functions, in elementary language

| Function | What it does |
| --- | --- |
| `Settings.credentials()` | Reads the server's token hashes and their assigned identities. It rejects duplicate tokens so one token cannot mean two people. |
| `Settings.embedding_space` | Gives each embedding configuration a name. This stops a search from comparing vectors made by different models or dimensions. |
| `authenticate()` | Checks the supplied token against hashes stored by the server. The server supplies the person's tenant, region, and role. |
| `require_admin()` | Checks that the person is an administrator. Other people cannot ingest policies or inspect readiness. |
| `suspicious_instruction()` | Looks for common attempts to override instructions or obtain secrets. This extra check does not replace database access rules. |
| `safety_response()` | Spots questions that need private HR help and returns a safe handoff. It runs before sending the question to a model. |
| `parse_policy()` | Reads the metadata and text in a Markdown file and checks their shape. It makes a content fingerprint so repeated files can be recognized. |
| `chunk_sections()` | Breaks the policy into small pieces at headings and word boundaries. Each piece keeps its heading and exact words. |
| `terms()` | Makes a small set of normalized words for the offline mock. It does not understand language like a trained embedding model. |
| `validate_vectors()` | Checks that every vector has the right length and usable numbers. Bad vectors are rejected instead of being stored or searched. |
| `Providers.post()` | Makes one request to the configured model server with a timeout. It keeps authentication details out of prompts. |
| `Providers.embed()` | Converts text into numbers for similarity comparisons. It uses either the offline mock or an embeddings API. |
| `Providers.select()` | Chooses source IDs that support the question, or declines. It is not allowed to write the final answer. |
| `connect()` | Opens a database transaction for a small piece of work. Successful work is saved, and failed work is rolled back. |
| `initialize()` | Creates the first version of the app's database tables and pgvector extension. It uses the separate policy database. |
| `ingest()` | Stores a policy and its chunks together, or recognizes an identical repeat. An existing version with different content is rejected. |
| `retrieve()` | Finds current chunks the person is allowed to read, then ranks their vectors by similarity. The access check happens before the top results are chosen. |
| `grounded_answer()` | Checks that selected IDs belong to the allowed evidence. It copies exact source text into the answer and attaches citations. |
| `ask_policy()` | Runs safety checks, retrieval, and evidence selection in order. It declines when there is not enough evidence. |
| `RequestSizeLimit.__call__()` | Counts bytes as an incoming request arrives. It stops an oversized request before the application parses it. |
| `create_app()` | Connects the functions to FastAPI routes and the chat page. It adds authentication, input checks, and safe error responses. |
| `identity()` / `admin()` route dependencies | Run the appropriate access checks before a route does its work. Routes use their checked result rather than trusting extra client fields. |
| `me()` | Shows the identity resolved by the server and the configured provider modes. It never returns tokens. |
| `health()` | Checks that the database tables can be reached. Only an administrator can see the result. |
| `ingest_documents()` | Accepts a batch from an administrator and runs ingestion in one transaction. It reports conflicts and invalid input without echoing policy text. |
| `ask()` | Accepts a question and returns an answer, a refusal, an abstention, or a handoff. It adds a request ID and hides provider error details. |
| `chat()` | Sends a chat request through n8n using the same caller token. It checks the structured reply before returning it to the browser. |
| Local Qwen helper `ready()` / `main()` | Checks that the Mac is serving the expected model. It reuses that server or starts AI-OS's existing Qwen command with a local log. |
| Browser `appendMessage()` / submit handlers | Show the question, answer, and expandable citations as plain text. They keep the token only in memory and display recoverable connection errors. |

The command-line scripts are intentionally small: `configure.py` creates local
credentials, `ingest.py` uploads policy files, `example_requests.py` sends one
question, and `smoke.py` checks the live Docker path. They do not send messages
to real employees or create HR cases.
