# app.py
# ============================================================
# Streamlit dashboard: Whole-class sensitivity analysis
# - Two datasets: Woolworths + Coles
# - Interactive filters (Approach, FWO, Set-off, 557C)
# - Interactive bar chart with TOP value labels
# - “Scenario cards” + quick stats
# ============================================================

import re
import pandas as pd
import streamlit as st
import plotly.express as px
import html
import textwrap

# -----------------------------
# Helpers
# -----------------------------
def money_fmt(v: float) -> str:
    # A$ with adaptive units
    if v >= 1_000_000_000:
        return f"A${v/1_000_000_000:.2f}B"
    if v >= 1_000_000:
        return f"A${v/1_000_000:.2f}M"
    if v >= 1_000:
        return f"A${v/1_000:.2f}K"
    return f"A${v:,.2f}"


def wrap_label(s, width=32):
    return "<br>".join(textwrap.wrap(s, width))

def parse_features_and_tags(text: str):
    """
    Extract consistent tags from scenario strings.
    Works for both Woolworths and Coles strings (best effort).
    """
    t = text.lower()

    # Approach
    if "judgement based" in t:
        approach = "Judgement Based"
    elif "coles based" in t:
        approach = "Coles Based"
    else:
        approach = "Unknown"

    # FWO
    if "without fwo" in t:
        fwo = "Without FWO"
    elif "with fwo" in t or "after fwo" in t:
        fwo = "With FWO"
    else:
        fwo = "Unknown"

    # Set-off
    setoff = "Unknown"
    if "set-off" in t:
        # Capture after "set-off:" or "set-off:" variations
        m = re.search(r"set-off\s*:\s*([a-z\s-]+)", t)
        if m:
            setoff = m.group(1).strip().title()
        else:
            # Alternate like "|Set-off: Annual |"
            m2 = re.search(r"set-off\s*[:]\s*([a-z\s-]+)\s*\|", t)
            if m2:
                setoff = m2.group(1).strip().title()
            else:
                # fallback keywords
                if "pay period" in t:
                    setoff = "Pay Period"
                elif "annual" in t:
                    setoff = "Annual"
                elif "bi annual" in t or "bi-annual" in t or "biannual" in t:
                    setoff = "Bi Annual"

    # 557C
    cond_557c = "N/A"
    if "557c" in t:
        if "all shifts" in t:
            cond_557c = "All Shifts"
        elif "non-clocked" in t or "non clocked" in t:
            cond_557c = "Non-Clocked Shifts"
        else:
            cond_557c = "557C (Unspecified)"

    # Clause
    clause = "28.11" if "28.11" in t else "Unknown"

    # A short label (for axis)
    short = text
    short = short.replace("Apporach", "Approach")
    short = re.sub(r"\s*\|\s*", " | ", short).strip()

    return {
        "approach": approach,
        "fwo": fwo,
        "setoff": setoff,
        "cond_557c": cond_557c,
        "clause": clause,
        "label": short,
    }

def make_df(rows, default_colors=None):
    df = pd.DataFrame(rows)
    if "color" not in df.columns:
        df["color"] = None
    if default_colors:
        # fill missing colors in order
        missing = df["color"].isna()
        df.loc[missing, "color"] = [default_colors[i] for i in range(missing.sum())]
    tags = df["category"].apply(parse_features_and_tags).apply(pd.Series)
    df = pd.concat([df, tags], axis=1)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["value_m"] = df["value"] / 1_000_000
    return df

# -----------------------------
# Data (yours, structured)
# -----------------------------
WOOLWORTHS_ROWS = [
    {
        "category": "Judgement Based Clause 28.11 Apporach | Without FWO | Set-off: Pay Period",
        "value": 1668147026.75,
        "color": "#10b981",
        "features": [
            "Clause 28.11: Judgement Based Approach",
            "FWO Cut Status: Without FWO",
            "Set-off: Pay Period",
        ],
    },
    {
        "category": "Judgement Based Clause 28.11 Apporach | With FWO | Set-off: Bi Annual",
        "value": 1371946816.29,
        "color": "#06b6d4",
        "features": [
            "Clause 28.11: Judgement Based Approach",
            "FWO Cut Status: With FWO Applied",
            "Set-off: Bi Annual",
        ],
    },
    {
        "category": "Coles Based Clause 28.11 Approach |Without FWO | Set-off: Bi Annual",
        "value": 409657215.48,
        "color": "#3b82f6",
        "features": [
            "Clause 28.11: Coles Based Approach",
            "FWO Cut Status: Without FWO",
            "Set-off: Bi Annual",
        ],
    },
    {
        "category": "Judgement Based Clause 28.11 Apporach | With FWO | Set-off: Pay Period",
        "value": 326116709.40,
        "color": "#f59e0b",
        "features": [
            "Clause 28.11: Judgement Based Approach",
            "FWO Cut Status: With FWO Applied",
            "Set-off: Pay Period",
        ],
    },
    {
        "category": "Coles Based Clause 28.11 Approach | With FWO | Set-off: Bi Annual",
        "value": 56690258.85,
        "color": "#8b5cf6",
        "features": [
            "Clause 28.11: Coles Based Approach",
            "FWO Cut Status: With FWO Applied",
            "Set-off: Bi Annual",
        ],
    },
]

COLES_ROWS = [
    {
        "category": "Judgement Based Clause 28.11 Apporach  | Set-off: Pay period | 557C condition on all shifts",
        "value": 780652186.32,
        "color": "#10b981",
        "features": [
            "Clause 28.11: Judgement Based Approach",
            "FWO Cut Status: Without FWO",
            "Set-off: Pay Period",
            "557C Condition: All Shifts",
        ],
    },
    {
        "category": "Judgement Based Clause 28.11 Apporach | Set-off: Pay period | 557C condition on non-clocked shifts",
        "value": 690773333.38,
        "color": "#06b6d4",
        "features": [
            "Clause 28.11: Judgement Based Approach",
            "FWO Cut Status: Without FWO",
            "Set-off: Pay Period",
            "557C Condition: Non-clocked shifts",
            "Best on Judgement",
        ],
    },
    {
        "category": "Judgement Based Clause 28.11 Apporach | Set-off: Pay period | 557C condition on non-clocked shifts | After FWO",
        "value": 282887638.08,
        "color": "#3b82f6",
        "features": [
            "Clause 28.11: Judgement Based Approach",
            "FWO Cut Status: With FWO Applied",
            "Set-off: Pay Period",
            "557C Condition: Non-clocked shifts",
            "Likely Best",
        ],
    },
    {
        "category": "Coles Based Clause 28.11 Apporach |Set-off: Annual | 557C condition on all shifts | After FWO",
        "value": 37575310.68,
        "color": "#f59e0b",
        "features": [
            "Clause 28.11: Coles Based Approach",
            "FWO Cut Status: With FWO Applied",
            "Set-off: Annual",
            "557C Condition: All Shifts",
        ],
    },
    {
        "category": "Coles Based Clause 28.11 Approach |Set-off: Annual | 557C condition on non-clocked shifts | After FWO",
        "value": 26617692.75,
        "color": "#8b5cf6",
        "features": [
            "Clause 28.11: Coles Based Approach",
            "FWO Cut Status: With FWO Applied",
            "Set-off: Annual",
            "557C Condition: Non-clocked shifts",
            "Likely Worst",
        ],
    },
]

df_woolies = make_df(WOOLWORTHS_ROWS)
df_coles = make_df(COLES_ROWS)

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="Sensitivity Analysis Dashboard", layout="wide")

# Minimal dark-ish polish (optional)
st.markdown(
    """
<style>
.block-container {padding-top: 1.2rem;}
small {opacity: 0.8;}
.card {
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 14px;
  padding: 14px 14px;
  background: rgba(255,255,255,0.02);
}
.card h4 {margin: 0 0 6px 0;}
.badge {
  display:inline-block; padding: 2px 8px; border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.14); margin-right: 6px;
  font-size: 12px; opacity: 0.9;
}
hr {opacity: 0.15;}
</style>
""",
    unsafe_allow_html=True,
)

st.title("Comparative Sensitivity Analysis")
st.caption("Interactive dashboard for whole-class scenario comparisons (Woolworths + Coles).")

tab1, tab2 = st.tabs(["Woolworths Class Action", "Coles Class Action"])

#def dashboard(df: pd.DataFrame, show_557c_filter: bool):
def dashboard(df: pd.DataFrame, show_557c_filter: bool, key_prefix: str):
    # Sidebar filters
    with st.sidebar:
        st.header("Filters")

        approach_opts = ["All"] + sorted([x for x in df["approach"].dropna().unique()])
        fwo_opts      = ["All"] + sorted([x for x in df["fwo"].dropna().unique()])
        setoff_opts   = ["All"] + sorted([x for x in df["setoff"].dropna().unique()])

        approach_sel = st.selectbox(
            "Approach", approach_opts, index=0,
            key=f"{key_prefix}_approach"
        )
        fwo_sel = st.selectbox(
            "FWO", fwo_opts, index=0,
            key=f"{key_prefix}_fwo"
        )
        setoff_sel = st.selectbox(
            "Set-off", setoff_opts, index=0,
            key=f"{key_prefix}_setoff"
        )

        cond_sel = "All"
        if show_557c_filter:
            cond_opts = ["All"] + sorted([x for x in df["cond_557c"].dropna().unique()])
            cond_sel = st.selectbox(
                "557C Condition", cond_opts, index=0,
                key=f"{key_prefix}_557c"
            )

        st.divider()

        sort_by = st.radio(
            "Sort bars",
            ["Value (desc)", "Value (asc)", "Original order"],
            index=0,
            key=f"{key_prefix}_sort"
        )

        show_table = st.toggle(
            "Show data table",
            value=False,
            key=f"{key_prefix}_table"
        )


    # Apply filters
    dff = df.copy()
    if approach_sel != "All":
        dff = dff[dff["approach"] == approach_sel]
    if fwo_sel != "All":
        dff = dff[dff["fwo"] == fwo_sel]
    if setoff_sel != "All":
        dff = dff[dff["setoff"] == setoff_sel]
    if show_557c_filter and cond_sel != "All":
        dff = dff[dff["cond_557c"] == cond_sel]

    # Sort
    if sort_by == "Value (desc)":
        dff = dff.sort_values("value", ascending=False)
    elif sort_by == "Value (asc)":
        dff = dff.sort_values("value", ascending=True)

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    if len(dff) == 0:
        c1.metric("Scenarios", "0")
        c2.metric("Max", "—")
        c3.metric("Min", "—")
        c4.metric("Spread (Max - Min)", "—")
        st.warning("No scenarios match the current filters.")
        return

    v_max = float(dff["value"].max())
    v_min = float(dff["value"].min())
    v_sum = float(dff["value"].sum())

    c1.metric("Scenarios", f"{len(dff)}")
    c2.metric("Max scenario", money_fmt(v_max))
    c3.metric("Min scenario", money_fmt(v_min))
    c4.metric("Spread", money_fmt(v_max - v_min))

    # Chart
    # - labels shown ABOVE bars via textposition="outside"
    # - use color column (hex)
    dff = dff.copy()
    dff["label_wrapped"] = dff["label"].apply(lambda x: wrap_label(x, width=32))
    fig = px.bar(
        dff,
        x="label_wrapped",
        y="value",
        text=dff["value"].apply(money_fmt),
        color="label",
        color_discrete_sequence=dff["color"].tolist(),
        hover_data={
            "value": ":,.2f",
            "approach": True,
            "fwo": True,
            "setoff": True,
            "cond_557c": True,
        },
    )


    fig.update_traces(
        textposition="outside",
        cliponaxis=False,  # IMPORTANT: allows labels to sit above the plot area
    )
    fig.update_layout(
        showlegend=False,
        xaxis_title="Scenario",
        yaxis_title="Total Amount (A$)",
        margin=dict(l=30, r=30, t=30, b=120),
        height=520,
    )
    fig.update_yaxes(tickformat=",")
    fig.update_xaxes(tickangle=0)

    st.plotly_chart(fig, use_container_width=True)

    # Cards
    st.subheader("Scenario cards")
    cols = st.columns(min(5, len(dff)))
    for i, (_, row) in enumerate(dff.iterrows()):
        with cols[i % len(cols)]:
            badges = []
            if row["approach"] != "Unknown":
                badges.append(row["approach"])
            if row["fwo"] != "Unknown":
                badges.append(row["fwo"])
            if row["setoff"] != "Unknown":
                badges.append(f"Set-off: {row['setoff']}")
            if show_557c_filter and row["cond_557c"] not in ["N/A", "Unknown"]:
                badges.append(f"557C: {row['cond_557c']}")

            feats = row.get("features", []) or []
            #feats_html = "".join([f"<li>{st._utils.escape_markdown(f)}</li>" for f in feats])
            feats_html = "".join([f"<li>{f}</li>" for f in feats])


            st.markdown(
                f"""
<div class="card">
  <h4 style="color:{row['color']};">{money_fmt(float(row["value"]))}</h4>
  <div style="margin-bottom:8px;">
    {"".join([f'<span class="badge">{b}</span>' for b in badges])}
  </div>
  <small>{row["label"]}</small>
  <hr/>
  <ul style="margin: 0 0 0 18px;">
    {feats_html}
  </ul>
</div>
""",
                unsafe_allow_html=True,
            )

    # Table
    if show_table:
        st.subheader("Data table")
        show_cols = ["label", "value", "approach", "fwo", "setoff", "cond_557c"]
        st.dataframe(dff[show_cols].rename(columns={"label": "scenario"}), use_container_width=True)

    st.caption(f"Filtered total (sum of displayed scenarios): **{money_fmt(v_sum)}**")

with tab1:
    st.markdown("### Woolworths: whole-class sensitivity analysis")
    dashboard(df_woolies, show_557c_filter=False, key_prefix="woolies")



with tab2:
    st.markdown("### Coles: whole-class sensitivity analysis")
    dashboard(df_coles, show_557c_filter=True,  key_prefix="coles")

st.sidebar.caption("Tip: set 'Sort bars' to Value (desc) to match a 'ranked' view.")
