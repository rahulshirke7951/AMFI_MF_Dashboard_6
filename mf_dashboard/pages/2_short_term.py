# pages/2_short_term.py
import streamlit as st
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.filters import style_returns_df, bar_top_bottom, heatmap_category_returns, category_comparison_bar, plot_layout, get_group_col, C
import plotly.graph_objects as go

SHORT_MAP = {"return_7d":"1W","return_14d":"2W","return_30d":"1M","return_90d":"3M","return_180d":"6M"}

def show():
    st.markdown("""<div class="mf-header">
        <h1>📈 Short-Term Returns <span class="mf-badge">MOMENTUM</span></h1>
        <p>1W · 2W · 1M · 3M · 6M · Sub-type breadth · Distribution · Momentum ranking</p>
    </div>""", unsafe_allow_html=True)

    if not st.session_state.get("data_loaded"):
        st.warning("⚠️ Load data from the sidebar first."); return

    df   = st.session_state.get("filtered_df", st.session_state["df"])
    full = st.session_state["df"]
    if len(df) < len(full):
        st.markdown(f'<div class="active-filter-bar">🎛️ Filters active — <b>{len(df):,}</b> of <b>{len(full):,}</b> schemes</div>', unsafe_allow_html=True)

    present_map = {k:v for k,v in SHORT_MAP.items() if k in df.columns}
    if not present_map:
        st.error("No short-term return columns found."); return

    # ── KPI cards with sparkline-style progress bar + gauge ring ─────────────
    cols = st.columns(len(present_map))
    for i,(col_key,label) in enumerate(present_map.items()):
        s = df[col_key].dropna()
        if s.empty: continue
        avg     = s.mean()
        pos     = int((s>0).sum())
        neg     = int((s<0).sum())
        pct_pos = pos / max(len(s),1) * 100
        color   = C["green"] if avg>=0 else C["red"]
        sign    = "+" if avg>=0 else ""
        bar_w   = f"{pct_pos:.0f}%"
        # Sentiment label
        if pct_pos >= 65:   sentiment = "🟢 Strong"
        elif pct_pos >= 50: sentiment = "🟡 Mixed"
        elif pct_pos >= 35: sentiment = "🟠 Weak"
        else:               sentiment = "🔴 Bearish"
        cols[i].markdown(f"""
        <div class="kpi-card" style="padding:14px 16px">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value" style="color:{color};font-size:1.6rem">{sign}{avg:.1f}%</div>
            <div style="margin:8px 0 4px;background:#E2E8F0;border-radius:6px;height:6px;overflow:hidden">
                <div style="background:{color};width:{bar_w};height:100%;border-radius:6px;transition:width 0.4s"></div>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-top:4px">
                <div style="font-size:0.67rem;color:#64748B">{sentiment}</div>
                <div style="font-size:0.67rem;color:#94A3B8">▲{pos} ▼{neg}</div>
            </div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # Tab order: Heatmap, Top&Bottom, Breadth, Distribution, Sub-Type Comparison, Scheme Table (last)
    tab_hm, tab_tb, tab_br, tab_dist, tab_cat, tab_table = st.tabs([
        "🔥 Sub-Type Heatmap","🏆 Top & Bottom","📊 Breadth by Sub-Type",
        "📐 Distribution","🎯 Sub-Type Comparison","📋 Scheme Table"
    ])

    grp = get_group_col(df)

    with tab_hm:
        fig_hm = heatmap_category_returns(df, present_map, group_col=grp)
        if fig_hm.data:
            st.plotly_chart(fig_hm, use_container_width=True)
        else:
            st.info("Not enough data — try removing filters.")

    with tab_tb:
        col_a, col_b = st.columns(2)
        with col_a: sel_tb = st.selectbox("Period", list(present_map.keys()), format_func=lambda x:present_map[x], key="st_tb")
        with col_b: n_show = st.slider("N per side", 5, 25, 10, key="st_n")
        st.plotly_chart(bar_top_bottom(df, sel_tb, present_map[sel_tb], n_show), use_container_width=True)

    with tab_br:
        sel_br = st.selectbox("Period", list(present_map.keys()), format_func=lambda x:present_map[x], key="st_br")
        if grp in df.columns:
            breadth_df = (
                df[~df[grp].isin(("NA","","Unknown"))]
                .groupby(grp)[sel_br]
                .apply(lambda x: (x>0).mean()*100).reset_index()
                .rename(columns={sel_br:"Breadth%", grp:"Sub-Type"})
                .sort_values("Breadth%", ascending=False)
            )
            colors = [C["green"] if v>=50 else C["red"] for v in breadth_df["Breadth%"]]
            fig_br = go.Figure(go.Bar(
                x=breadth_df["Sub-Type"], y=breadth_df["Breadth%"],
                marker_color=colors, marker_line_width=0,
                text=[f"{v:.0f}%" for v in breadth_df["Breadth%"]], textposition="outside",
                textfont=dict(family="DM Mono, monospace", size=11, color="#475569"),
            ))
            fig_br.add_hline(y=50, line_dash="dash", line_color="#CBD5E1",
                             annotation_text="50% neutral", annotation_font_color="#94A3B8")
            fig_br.update_layout(**plot_layout(
                title=f"Market Breadth by Sub-Type — {present_map[sel_br]} (% schemes positive)",
                height=400, xaxis=dict(tickangle=-30),
            ))
            st.plotly_chart(fig_br, use_container_width=True)
            st.caption("Above 50% = majority of schemes in that sub-type are positive. Below 50% = majority are negative.")

    with tab_dist:
        sel_d = st.selectbox("Period", list(present_map.keys()), format_func=lambda x:present_map[x], key="st_dist")
        data  = df[sel_d].dropna()
        if not data.empty:
            fig_d = go.Figure()
            fig_d.add_trace(go.Histogram(x=data, nbinsx=50, marker_color=C["blue"], opacity=0.75,
                                          marker_line_color="#FFFFFF", marker_line_width=0.5))
            fig_d.add_vline(x=data.mean(),   line_color=C["amber"], line_dash="dash",
                             annotation_text=f"Avg {data.mean():+.1f}%", annotation_font_color=C["amber"])
            fig_d.add_vline(x=data.median(), line_color=C["green"], line_dash="dot",
                             annotation_text=f"Median {data.median():+.1f}%", annotation_font_color=C["green"])
            fig_d.add_vline(x=0, line_color=C["red"], line_width=1.5)
            fig_d.update_layout(**plot_layout(title=f"Return Distribution — {present_map[sel_d]}", height=360))
            st.plotly_chart(fig_d, use_container_width=True)
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                st.table(pd.DataFrame({
                    "Percentile": ["5th","25th","50th","75th","90th","95th"],
                    "Return":     [f"{np.percentile(data,p):+.2f}%" for p in [5,25,50,75,90,95]],
                }))
            with col_p2:
                st.metric("% Positive", f"{(data>0).mean()*100:.1f}%")
                st.metric("Std Dev",    f"{data.std():.2f}%")

    with tab_cat:
        sel_c = st.selectbox("Period", list(present_map.keys()), format_func=lambda x:present_map[x], key="st_cat")
        st.plotly_chart(category_comparison_bar(df, sel_c, present_map[sel_c]), use_container_width=True)
        st.caption("Error bars = std deviation within sub-type. Diamond = median.")

    with tab_table:
        # Clean table — only Scheme name + return columns
        sort_col = st.selectbox("Sort by", list(present_map.keys()), format_func=lambda x:present_map[x], key="st_sort")
        asc      = st.checkbox("Ascending", value=False, key="st_asc")
        disp_cols = ["scheme_name","latest_nav"] + list(present_map.keys())
        disp_cols = [c for c in disp_cols if c in df.columns]
        disp      = df[disp_cols].sort_values(sort_col, ascending=asc).reset_index(drop=True)
        disp.index += 1
        rename = {**present_map, "scheme_name":"Scheme", "latest_nav":"NAV"}
        disp   = disp.rename(columns=rename)
        st.dataframe(style_returns_df(disp, list(present_map.values())), use_container_width=True, height=500)
        st.download_button("⬇️ Download CSV", df[disp_cols].to_csv(index=False), "short_term.csv","text/csv")

show()
