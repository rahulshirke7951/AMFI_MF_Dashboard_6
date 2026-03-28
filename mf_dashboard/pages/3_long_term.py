# pages/3_long_term.py
import streamlit as st
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.filters import style_returns_df, bar_top_bottom, heatmap_category_returns, category_comparison_bar, plot_layout, get_group_col, C
import plotly.graph_objects as go

LONG_MAP = {"return_365d":"1Y","return_730d":"2Y","return_1095d":"3Y","cagr_2y":"2Y CAGR","cagr_3y":"3Y CAGR"}

def compute_cagr(ret_pct, years):
    """Convert absolute % return to CAGR."""
    if pd.isna(ret_pct): return np.nan
    return ((1 + ret_pct/100) ** (1/years) - 1) * 100

def consistency_score(row, ret_cols):
    vals = [row.get(c) for c in ret_cols if c in row and pd.notna(row.get(c))]
    if not vals: return np.nan
    return sum(v>0 for v in vals)/len(vals)*100

def show():
    st.markdown("""<div class="mf-header">
        <h1>📊 Long-Term Returns <span class="mf-badge">COMPOUNDING</span></h1>
        <p>1Y · 2Y · 3Y CAGR · Percentile rank · Consistency · Sub-type comparison</p>
    </div>""", unsafe_allow_html=True)

    if not st.session_state.get("data_loaded"):
        st.warning("⚠️ Load data from the sidebar first."); return

    df   = st.session_state.get("filtered_df", st.session_state["df"]).copy()
    full = st.session_state["df"]
    if len(df) < len(full):
        st.markdown(f'<div class="active-filter-bar">🎛️ Filters active — <b>{len(df):,}</b> of <b>{len(full):,}</b> schemes</div>', unsafe_allow_html=True)

    present_map = {k:v for k,v in LONG_MAP.items() if k in df.columns}
    if not present_map:
        st.error("No long-term return columns found."); return

    # ── Derived columns ────────────────────────────────────────────────────
    all_ret_cols = list({"return_7d","return_14d","return_30d","return_90d",
                          "return_180d","return_365d","return_730d","return_1095d"} & set(df.columns))
    df["consistency_score"] = df.apply(lambda r: consistency_score(r, all_ret_cols), axis=1)

    # 2Y CAGR — derived from return_730d
    if "cagr_2y" not in df.columns and "return_730d" in df.columns:
        df["cagr_2y"] = df["return_730d"].apply(lambda x: compute_cagr(x, 2))
    # 1Y CAGR = same as 1Y return
    if "cagr_1y" not in df.columns and "return_365d" in df.columns:
        df["cagr_1y"] = df["return_365d"].copy()

    grp = get_group_col(df)
    if grp in df.columns and "return_365d" in df.columns:
        df["peer_rank_1y"] = df.groupby(grp)["return_365d"].rank(pct=True) * 100

    # ── KPI tiles ──────────────────────────────────────────────────────────
    display_periods = {**present_map}
    if "cagr_2y" in df.columns: display_periods["cagr_2y"] = "2Y CAGR"
    kpi_cols = list(present_map.items())

    cols = st.columns(len(kpi_cols) + 1)
    for i,(col_key,label) in enumerate(kpi_cols):
        valid = df[col_key].dropna()
        if valid.empty: continue
        avg = valid.mean(); med = valid.median(); top10 = valid.quantile(0.90)
        color = C["green"] if avg>=0 else C["red"]
        sign  = "+" if avg>=0 else ""
        cols[i].markdown(f"""<div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value" style="color:{color}">{sign}{avg:.1f}%</div>
            <div class="kpi-sub">Median: {med:+.1f}% · Top 10%: {top10:+.1f}%</div>
        </div>""", unsafe_allow_html=True)

    cons_avg = df["consistency_score"].mean()
    cols[len(kpi_cols)].markdown(f"""<div class="kpi-card">
        <div class="kpi-label">AVG CONSISTENCY <span title="% of return periods (1W to 3Y) where the scheme delivered positive returns. Higher = more reliable." style="cursor:help;color:#94A3B8">ⓘ</span></div>
        <div class="kpi-value" style="color:{C['blue']}">{cons_avg:.0f}%</div>
        <div class="kpi-sub">% periods with +ve return</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # Tab order: Heatmap, Top&Bottom, Distribution, Sub-Type Comparison, Scheme Table (last)
    tab_hm, tab_tb, tab_dist, tab_cat, tab_table = st.tabs([
        "🔥 Sub-Type Heatmap","🏆 Top & Bottom","📐 Distribution","🎯 Sub-Type Comparison","📋 Scheme Table"
    ])

    with tab_hm:
        fig_hm = heatmap_category_returns(df, present_map, group_col=grp)
        if fig_hm.data:
            st.plotly_chart(fig_hm, use_container_width=True)
        else:
            st.info("Not enough data for heatmap.")

    with tab_tb:
        col_a, col_b = st.columns(2)
        with col_a: sel = st.selectbox("Period", list(present_map.keys()), format_func=lambda x:present_map[x], key="lt_sel")
        with col_b: n_show = st.slider("N per side", 5, 25, 10, key="lt_n")
        st.plotly_chart(bar_top_bottom(df, sel, present_map[sel], n_show), use_container_width=True)

    with tab_dist:
        sel_d = st.selectbox("Period", list(present_map.keys()), format_func=lambda x:present_map[x], key="lt_dist")
        data  = df[sel_d].dropna()
        if not data.empty:
            fig = go.Figure()
            fig.add_trace(go.Histogram(x=data, nbinsx=50, marker_color=C["blue"], opacity=0.75,
                                        marker_line_color="#FFFFFF", marker_line_width=0.5))
            fig.add_vline(x=data.mean(),   line_color=C["amber"], line_dash="dash",
                          annotation_text=f"Avg {data.mean():+.1f}%",   annotation_font_color=C["amber"])
            fig.add_vline(x=data.median(), line_color=C["green"], line_dash="dot",
                          annotation_text=f"Median {data.median():+.1f}%", annotation_font_color=C["green"])
            fig.add_vline(x=0, line_color=C["red"], line_width=1.5)
            fig.update_layout(**plot_layout(title=f"Return Distribution — {present_map[sel_d]}", height=360))
            st.plotly_chart(fig, use_container_width=True)
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                st.table(pd.DataFrame({
                    "Percentile": ["5th","10th","25th","50th","75th","90th","95th"],
                    "Return":     [f"{np.percentile(data,p):+.2f}%" for p in [5,10,25,50,75,90,95]],
                }))
            with col_p2:
                st.metric("% Positive", f"{(data>0).mean()*100:.1f}%")
                st.metric("Std Dev",    f"{data.std():.2f}%")
                st.metric("Skewness",   f"{data.skew():.2f}")

    with tab_cat:
        sel_c = st.selectbox("Period", list(present_map.keys()), format_func=lambda x:present_map[x], key="lt_cat")
        st.plotly_chart(category_comparison_bar(df, sel_c, present_map[sel_c]), use_container_width=True)
        st.caption("Error bars = std deviation. Diamond = median. Wider bars = more spread within sub-type.")

    with tab_table:
        sort_col = st.selectbox("Sort by", list(present_map.keys()), format_func=lambda x:present_map[x], key="lt_sort")
        asc      = st.checkbox("Ascending", value=False, key="lt_asc")

        # Build display dataframe — only columns that actually exist
        rows = df.sort_values(sort_col, ascending=asc).reset_index(drop=True)
        rows.index += 1

        out = pd.DataFrame()
        out["Scheme"]  = rows["scheme_name"]
        if "latest_nav" in rows.columns:
            out["NAV"] = rows["latest_nav"]

        # Return period columns
        for col, label in present_map.items():
            if col in rows.columns:
                out[label] = rows[col]

        # CAGR columns — compute cleanly if not already present
        if "return_365d" in rows.columns:
            out["1Y CAGR"] = rows["return_365d"]
        
        if "cagr_2y" in rows.columns:
           out["2Y CAGR"] = rows["cagr_2y"]
        elif "return_730d" in rows.columns:
           out["2Y CAGR"] = rows["return_730d"].apply(
               lambda x: ((1 + x/100) ** (1/2) - 1) * 100 if pd.notna(x) else np.nan)

        if "cagr_3y" in rows.columns:
            out["3Y CAGR"] = rows["cagr_3y"]
        elif "return_1095d" in rows.columns:
            out["3Y CAGR"] = rows["return_1095d"].apply(
                lambda x: ((1 + x/100) ** (1/3) - 1) * 100 if pd.notna(x) else np.nan)

        if "consistency_score" in rows.columns:
            out["Consistency%"] = rows["consistency_score"]
        if "peer_rank_1y" in rows.columns:
            out["Peer%ile 1Y"] = rows["peer_rank_1y"]

        # Only colour columns that are actually numeric and present
        colour_cols = [c for c in ["1Y","2Y","3Y","1Y CAGR","2Y CAGR","3Y CAGR",
                                    "1M","3M","6M","1W","2W","Consistency%","Peer%ile 1Y"]
                       if c in out.columns and pd.api.types.is_numeric_dtype(out[c])]

        st.dataframe(style_returns_df(out, colour_cols), use_container_width=True, height=500)
        st.download_button("⬇️ Download CSV", out.to_csv(index=False), "long_term.csv", "text/csv")
show()
