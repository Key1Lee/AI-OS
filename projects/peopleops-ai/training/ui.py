"""Category A UI shell. Calls exercise-backed APIs without bypassing them."""
import uuid
import httpx
import streamlit as st
from lab.config import Settings

st.set_page_config(page_title="PeopleOps AI · Engineering lab", page_icon="◈", layout="wide")
st.markdown("""<style>
.stApp {background:#f5f7fa} [data-testid='stSidebar'] {background:#102b32}
[data-testid='stSidebar'] * {color:#f0f5f3} h1,h2,h3 {letter-spacing:-.035em}
[data-testid='stMetric'] {background:white;padding:18px;border:1px solid #dfe6e7;border-radius:12px}
.stMainBlockContainer {max-width:1200px} .eyebrow{color:#2d756c;font-weight:700;letter-spacing:.15em;font-size:12px}
</style>""", unsafe_allow_html=True)
config = Settings()


def call(path, method="GET", payload=None, token=None):
    try:
        response = httpx.request(method, config.api_url + path, json=payload,
                                headers={"Authorization": "Bearer " + token} if token else {}, timeout=25)
        data = response.json()
        if response.status_code == 501:
            st.info(f"{data['exercise']} is ready for your implementation. The foundation remains available.")
            return None
        if response.is_error:
            st.error(f"HTTP {response.status_code} · {data.get('detail', data.get('message', 'Request failed'))}")
            return None
        return data
    except (httpx.HTTPError, ValueError):
        st.error("Backend is unavailable. Start the stack with docker compose up --build -d.")
        return None


with st.sidebar:
    st.markdown("## ◈ PeopleOps AI")
    st.caption("ENGINEERING LAB / SYNTHETIC DATA")
    page = st.radio("Workspace", ["Lab overview", "Data workbench", "Policy assistant", "Employee tools", "Actions", "Exercise path", "Operations"])
    st.divider()
    identities = call("/lab/identities") or []
    if not identities:
        st.stop()
    chosen = st.selectbox("Demo identity", identities, format_func=lambda x: x["name"])
    st.caption("Local identity simulator. Every record is fictional.")

token = chosen["token"]
st.markdown("<p class='eyebrow'>BUILD · TEST · EXPLAIN</p>", unsafe_allow_html=True)
st.title(page)

if page == "Lab overview":
    st.write("A working enterprise sandbox. Business logic is yours to build.")
    catalog = call("/lab/catalog")
    if catalog:
        cols = st.columns(4)
        for col, key in zip(cols, ["employees", "jobs", "recruiting_events", "policies"]):
            col.metric(key.replace("_", " ").title(), catalog["counts"][key])
        st.subheader("Start with one real problem")
        st.write("Workday sends Maya's name with extra spaces and her email in uppercase. Normalize one record before it reaches the employee table.")
        st.code('normalize_employee({"full_name": "  Maya   Chen  ", "email": " PERSON001@EXAMPLE.TEST ", ...})', language="python")
        st.info("Checkpoint 1 · exercises/e01_cleaning.py · 8 focused tests · no solution supplied")
        st.code("uv run pytest tests/exercises/test_e01_cleaning.py", language="bash")
        a, b, c = st.columns(3)
        a.markdown("**A · Foundation**\n\nContainers, models, fixtures, mocks, UI, tests, telemetry.")
        b.markdown("**B · Your implementation**\n\nPython, SQL, retrieval, permissions, actions, recovery.")
        c.markdown("**C · Staff extensions**\n\nScaling, concurrency, CI/CD, architecture tradeoffs.")
        st.caption("Fixture clock: 2026-10-01 · Seed: 42 · No paid API required")
elif page == "Data workbench":
    st.warning("Developer fixture explorer: all synthetic records are visible here. Employee permissions are exercised on Employee tools.")
    name = st.selectbox("Dataset", ["raw_employees", "employees", "invalid_employees", "jobs", "candidates", "raw_recruiting_events", "policies", "tickets", "onboarding_tasks", "slack_messages"])
    data = call("/lab/fixtures/" + name)
    if data:
        st.caption(f"{len(data['rows'])} fixture records")
        st.dataframe(data["rows"], hide_index=True, width="stretch")
        st.download_button("Download synthetic JSON", __import__("json").dumps(data["rows"], indent=2), name + ".json", "application/json")
elif page == "Policy assistant":
    st.write("Ask about payroll, PTO, benefits, onboarding, expenses, or parental leave.")
    with st.form("ask"):
        question = st.text_input("Policy question", "When is payroll paid?")
        submitted = st.form_submit_button("Ask with policy evidence")
    if submitted:
        result = call("/api/assistant", "POST", {"text": question}, token)
        if result:
            st.write(result["answer"])
            st.json(result["citations"])
    st.caption("Exercises E04–E06 build section provenance, permission filtering, and supported answers.")
elif page == "Employee tools":
    st.write(f"Acting as {chosen['employee_id']} · {chosen['role']}")
    employee = st.text_input("Employee ID", chosen["employee_id"])
    if st.button("Get employee and PTO balance"):
        result = call("/api/employees/" + employee, token=token)
        if result:
            st.json(result)
    candidate = st.text_input("Candidate ID", "CAN-001")
    if st.button("Get recruiting record"):
        result = call("/api/candidates/" + candidate, token=token)
        if result:
            st.json(result)
    if st.button("List job openings"):
        result = call("/api/jobs", token=token)
        if result:
            st.json(result)
elif page == "Actions":
    st.write("Preview a request, review its details, then explicitly confirm execution.")
    # Never carry a proposal across demo identities.
    if st.session_state.get("proposal_actor") != chosen["employee_id"]:
        st.session_state.pop("proposal", None)
    with st.form("prepare"):
        message = st.text_area("Request", "Employee needs help with payroll")
        prepared = st.form_submit_button("Prepare a preview")
    if prepared:
        result = call("/api/actions/prepare", "POST", {"text": message}, token)
        st.session_state.pop("proposal", None)
        if result and result.get("proposal_id"):
            st.session_state.proposal = result
            st.session_state.proposal_actor = chosen["employee_id"]
            st.session_state.action_key = str(uuid.uuid4())
        elif result:
            st.write(result)
    if st.session_state.get("proposal"):
        st.json(st.session_state.proposal)
        consent = st.checkbox("I confirm the exact request shown above.")
        if st.button("Confirm and execute", disabled=not consent):
            result = call("/api/actions/confirm", "POST", {"proposal_id": st.session_state.proposal["proposal_id"], "confirmed": consent,
                          "idempotency_key": st.session_state.action_key}, token)
            if result:
                st.json(result)
    request_id = st.text_input("Previous request ID", "TKT-001")
    if st.button("Check status"):
        result = call("/api/requests/" + request_id, token=token)
        if result:
            st.json(result)
elif page == "Exercise path":
    catalog = call("/lab/catalog")
    if catalog:
        for exercise in catalog["exercises"]:
            with st.expander(f"{exercise['id']} · {exercise['title']}", expanded=exercise["id"] == "E01"):
                st.write(exercise["problem"])
                st.code(exercise["file"], language=None)
                st.code(exercise["test"], language="bash")
                st.caption("Assessment: not attempted. Passing tests alone do not mark understanding complete.")
elif page == "Operations":
    st.write("Live process observations; request bodies and credentials are excluded.")
    if st.button("Run provider probe"):
        result = call("/lab/provider-probe", "POST")
        if result:
            st.json(result)
    state = call("/lab/telemetry")
    if state:
        a, b, c = st.columns(3)
        a.metric("Requests", state["requests"])
        b.metric("Errors", state["errors"])
        c.metric("Pending exercise calls", state["pending_exercises"])
        st.json({k: v for k, v in state.items() if k != "events"})
        st.dataframe(state["events"], width="stretch")
    st.caption("Mock fault controls are available at http://127.0.0.1:8801/docs. Run evaluations with uv run python -m lab.evaluate.")
