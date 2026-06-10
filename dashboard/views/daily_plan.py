"""Daily Plan tab — main working view for the Streamlit dashboard."""

import streamlit as st
from dashboard.state import load_plan, update_action_status


def render():
    """Render the Daily Plan tab."""
    st.header("📋 Daily Action Plan")

    plan = load_plan()
    if not plan:
        st.info("No plan found for today. Run `python run_pipeline.py` to generate one.")
        return

    col1, col2, col3 = st.columns(3)
    cap = plan.get("capacity", {})
    col1.metric("💬 Comments left", cap.get("comments_remaining", 0))
    col2.metric("🔗 Connections left", cap.get("connections_remaining", 0))
    col3.metric("👤 Visits left", cap.get("visits_remaining", 0))

    st.markdown("---")

    actions = plan.get("actions", [])
    if not actions:
        st.info("No suggested actions for today.")
        return

    for action in actions:
        with st.container():
            st.markdown(f"### {action.get('action_id', '')} — {action.get('type', '').upper()}")
            st.markdown(f"**Priority:** {action.get('priority', '')}  |  **Tier:** {action.get('tier', action.get('author_tier', ''))}")

            # Show person/post info
            if action["type"] == "comment":
                st.markdown(f"**Post:** [{action.get('post_preview', '')}]({action.get('url', '#')})")
                st.markdown(f"**Author:** {action.get('author_name', '')}")
            else:
                st.markdown(f"**Person:** [{action.get('person_name', '')}]({action.get('url', '#')})")
                st.markdown(f"**Headline:** {action.get('person_headline', '')}")
                if action.get("reason"):
                    st.markdown(f"**Reason:** {action['reason']}")

            # Suggested text
            texts = action.get("suggested_text", [])
            if texts:
                with st.expander("💡 Suggested text"):
                    for i, t in enumerate(texts, 1):
                        st.code(t, language="text")
                        if st.button(f"📋 Copy variant {i}", key=f"copy_{action['action_id']}_{i}"):
                            st.write("Text ready to copy (select and Ctrl+C / Cmd+C)")
                            st.code(t, language="text")

            # Status controls
            current_status = action.get("status", "suggested")
            cols = st.columns(4)
            with cols[0]:
                if st.button("✅ Done", key=f"done_{action['action_id']}"):
                    plan = update_action_status(plan, action["action_id"], "executed")
                    st.rerun()
            with cols[1]:
                if st.button("⏭️ Skip", key=f"skip_{action['action_id']}"):
                    plan = update_action_status(plan, action["action_id"], "skipped")
                    st.rerun()
            with cols[2]:
                if st.button("❌ Failed", key=f"fail_{action['action_id']}"):
                    plan = update_action_status(plan, action["action_id"], "failed")
                    st.rerun()
            with cols[3]:
                st.caption(f"Status: **{current_status}**")

            # Feedback expander
            with st.expander("📝 Submit feedback"):
                feedback = {}
                if action["type"] == "connection":
                    feedback["connection_accepted"] = st.checkbox("Connection accepted?", key=f"fb_ca_{action['action_id']}")
                if action["type"] == "comment":
                    feedback["reply_received"] = st.checkbox("Received a reply?", key=f"fb_rr_{action['action_id']}")
                notes = st.text_input("Notes", key=f"fb_notes_{action['action_id']}")
                if notes:
                    feedback["notes"] = notes
                if st.button("Save feedback", key=f"fb_save_{action['action_id']}"):
                    plan = update_action_status(plan, action["action_id"], current_status, feedback)
                    st.success("Feedback saved!")

            st.markdown("---")