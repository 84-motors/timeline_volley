
# app.py
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="データバレー（HTML出力付きMVP）", layout="wide")

REQUIRED_COLS = ["rally_no", "player", "skill", "detail", "point_to"]

# コード→ラベル
SKILL_LABELS = {
    "S": "サーブ",
    "R": "レセプション（サーブカット）",
    "T": "トス",
    "A": "アタックヒット",
    "B": "ブロック",
    "F": "フリーボール（チャンス返し）",
    "D": "ディグ（スパイクレシーブ）",
}
POINT_LABELS = {"U": "US（自チーム）", "O": "Opponent（敵チーム）", "I": "継続（in_play）"}

# ===== detail の説明（固定文言）=====
DETAIL_EXPLANATION = {
    "S": {  # サーブの質
        "title": "サーブの質",
        "A": "相手からチャンスボールで返球、もしくは即決定（サービスエース等）。",
        "B": "相手が二段トスのスパイクで返球（攻撃簡略・品質低下）。",
        "C": "相手が通常の攻撃で返球（効果薄）。",
        "M": "サーブ側のミス（フォルト等）。",
        "P": "プレッシャー下だが効果あり／特筆すべき良いサーブ（チーム内定義用）。",
    },
    "R": {  # レセプション（サーブカット）の質
        "title": "レセプション（サーブカット）の質",
        "A": "セッターが一歩動く程度の完璧なレシーブ（Aトス可能）。",
        "B": "セッターが動くがトスを上げられる（Bトス想定）。",
        "C": "セッターがアンダートス、もしくはセッターがトスできない（C相当）。",
        "M": "レセプションミス（ダイレクト失点・返球不能）。",
        "P": "厳しいサーブ下での質上ブレ（チーム内評価用）。",
    },
    "D": {  # ディグ（スパイクレシーブ）の質
        "title": "ディグ（スパイクレシーブ）の質",
        "A": "セッターが一歩動く程度の完璧なディグ（Aトス可能）。",
        "B": "セッターが動くがトスを上げられる（Bトス想定）。",
        "C": "セッターがアンダートス、もしくはセッターがトスできない（C相当）。",
        "M": "ディグミス（ラリー中断）。",
        "P": "強打・ブロックアウト後など難度高でも可用なレシーブ（評価用）。",
    },
    "T": {  # トスの質
        "title": "トスの質",
        "A": "完璧なトス（スパイカーが最適に打てる）。",
        "B": "トスが割れる、もしくはネットに近いがスパイカーが打てる。",
        "C": "スパイカーが打てない（返球やつなぎに切替）。",
        "M": "トスミス（ネット越え不能など）。",
        "P": "難条件下での良トス（評価用）。",
    },
    "A": {  # アタックヒット（任意運用）
        "title": "アタックヒットの質（チーム内定義用）",
        "A": "決定、もしくは相手を崩して次球チャンス。",
        "B": "効果あり（弱返球・チャンスボール誘発等）。",
        "C": "効果薄（通常返球）。",
        "M": "アタックミス。",
        "P": "プレッシャー下でも有効打（評価用）。",
    },
    "B": {  # ブロック（任意運用）
        "title": "ブロックの質（チーム内定義用）",
        "A": "シャットアウト、もしくは有効タッチでチャンスへ。",
        "B": "ワンタッチ等で相手攻撃品質を下げる。",
        "C": "効果薄（通常返球）。",
        "M": "ネットタッチ等のミス。",
        "P": "難条件下での良ブロック（評価用）。",
    },
    "F": {  # フリーボール（任意運用）
        "title": "フリーボール（チャンス返し）の質（チーム内定義用）",
        "A": "次の組立に最適な返球。",
        "B": "やや乱れるが次を組める。",
        "C": "乱れて攻撃に移れない。",
        "M": "返球ミス。",
        "P": "難条件下でも良返球（評価用）。",
    },
}

@st.cache_data
def load_data(file):
    # 余分な行は読み飛ばす
    df = pd.read_csv(file, on_bad_lines="skip")
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"必須列が不足しています: {missing}")
    df["rally_no"] = pd.to_numeric(df["rally_no"], errors="coerce").astype("Int64")
    for c in ["player", "skill", "detail", "point_to"]:
        df[c] = df[c].astype(str).str.strip().str.upper()
    # コード妥当性チェック
    valid_skill, valid_detail, valid_point = set(SKILL_LABELS.keys()), {"A","B","C","M","P"}, {"U","O","I"}
    bad = df[~df["skill"].isin(valid_skill) | ~df["detail"].isin(valid_detail) | ~df["point_to"].isin(valid_point)]
    if not bad.empty:
        st.warning(f"定義外コードの行が {len(bad)} 件あります。CSVを修正してください。")
    return df

def kpi(df):
    total = len(df)
    pts   = (df["point_to"] == "U").sum()
    lost  = (df["point_to"] == "O").sum()
    rate  = round(pts/total, 3) if total else 0.0
    return {"イベント数": total, "得点(U)": pts, "失点(O)": lost, "得点率(U/総)": rate}

# ===== HTML組み立てユーティリティ =====
def fig_to_html(fig, title):
    # Plotly本体はページのheadで1回だけ読み込むため、ここはinclude_plotlyjs=False
    return f"<section><h2>{title}</h2>" + fig.to_html(full_html=False, include_plotlyjs=False) + "</section>"

def table_to_html(df, title, note=""):
    html = f"<section><h2>{title}</h2>"
    if note:
        html += f"<p class='note'>{note}</p>"
    html += df.to_html(index=False, border=0, classes='dataframe')
    html += "</section>"
    return html

def kpi_to_html(vals):
    rows = "".join([f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in vals.items()])
    return f"<section><h2>KPI</h2><table class='kpi'>{rows}</table></section>"

def detail_explanation_html():
    blocks = []
    for code in ["S","R","D","T","A","B","F"]:
        exp = DETAIL_EXPLANATION.get(code, {})
        h = f"<section><h2>{SKILL_LABELS[code]}</h2><ul>"
        for key in ["A","B","C","M","P"]:
            txt = exp.get(key, "")
            h += f"<li><strong>{key}</strong>：{txt}</li>"
        h += "</ul></section>"
        blocks.append(h)
    return "".join(blocks)

def assemble_export_html(kpi_vals, fig_player, fig_skill, fig_detail, fig_timeline, df_table_html, help_html):
    head = """
<!DOCTYPE html><html lang='ja'><head>
<meta charset='utf-8'>
<title>データバレー レポート</title>
<script src='https://cdn.plot.ly/plotly-2.30.0.min.js'></script>
<style>
  body { font-family: system-ui, -apple-system, 'Segoe UI', Roboto, 'Noto Sans JP', sans-serif; margin: 24px; }
  h1 { margin-top: 0; }
  h2 { margin: 24px 0 8px; border-left: 6px solid #3b82f6; padding-left: 8px; }
  section { margin-bottom: 24px; }
  .kpi { border-collapse: collapse; }
  .kpi th { text-align: left; padding: 6px 10px; background: #f3f4f6; }
  .kpi td { padding: 6px 10px; }
  .note { color: #6b7280; }
  table.dataframe { border-collapse: collapse; width: 100%; }
  table.dataframe th, table.dataframe td { border: 1px solid #e5e7eb; padding: 6px 10px; }
</style>
</head><body>
<h1>データバレー レポート</h1>
"""
    body = (
        kpi_to_html(kpi_vals) +
        fig_to_html(fig_player, "選手別 得点数（U）") +
        fig_to_html(fig_skill,  "スキル別 得点数（U）") +
        fig_to_html(fig_detail, "ディテール（質）別 得点数（U）") +
        fig_to_html(fig_timeline, "タイムライン（U=+1, I=0, O=-1）") +
        help_html +
        df_table_html
    )
    tail = "</body></html>"
    return head + body + tail

st.title("🏐 データバレー（HTML出力付きMVP）")

# --- サイドバー：データ ---
with st.sidebar:
    st.header("データ")
    uploaded = st.file_uploader("CSVをアップロード", type=["csv"])
    use_sample = st.checkbox("サンプル（data_sample_50_v2.csv）を使う", value=True)
    if uploaded:
        df = load_data(uploaded)
    elif use_sample:
        df = load_data("data/data_sample_50_v2.csv")
    else:
        st.stop()

    st.divider()
    st.header("フィルタ")
    player_sel = st.multiselect("選手", sorted(df["player"].unique()))
    skill_sel_codes = st.multiselect(
        "スキル（コード）", sorted(SKILL_LABELS.keys()),
        format_func=lambda k: f"{k}：{SKILL_LABELS[k]}"
    )
    point_sel_codes = st.multiselect(
        "ポイント（コード）", ["U","O","I"],
        format_func=lambda k: f"{k}：{POINT_LABELS[k]}"
    )
    detail_sel_codes = st.multiselect("ディテール（質）", ["A","B","C","M","P"])

def apply_filters(df):
    q = df.copy()
    if player_sel:        q = q[q["player"].isin(player_sel)]
    if skill_sel_codes:   q = q[q["skill"].isin(skill_sel_codes)]
    if point_sel_codes:   q = q[q["point_to"].isin(point_sel_codes)]
    if detail_sel_codes:  q = q[q["detail"].isin(detail_sel_codes)]
    return q

qdf = apply_filters(df)

# KPI
vals = kpi(qdf)
col1, col2, col3, col4 = st.columns(4)
for col, (k,v) in zip([col1,col2,col3,col4], vals.items()):
    col.metric(k, v)

st.divider()

# ===== 可視化用の図（レポート出力でも再利用）=====
# 1) 選手別
gp = qdf.groupby("player")["point_to"].apply(lambda s: (s=="U").sum()).reset_index(name="points_U")
fig_player = px.bar(gp, x="player", y="points_U", title="選手別 得点数（U）")

# 2) スキル別（ラベル化）
qs = qdf.copy()
qs["skill_label"] = qs["skill"].map(SKILL_LABELS)
gs = qs.groupby("skill_label")["point_to"].apply(lambda s: (s=="U").sum()).reset_index(name="points_U")
fig_skill = px.bar(gs, x="skill_label", y="points_U", title="スキル別 得点数（U）")

# 3) ディテール別
gd = qdf.groupby("detail")["point_to"].apply(lambda s: (s=="U").sum()).reset_index(name="points_U")
fig_detail = px.bar(gd, x="detail", y="points_U", title="ディテール（質）別 得点数（U）")

# 4) タイムライン（ステップ表示＋I区間ハイライト）
tl = qdf.copy().sort_values("rally_no")
tl["y"] = tl["point_to"].map({"U":1, "I":0, "O":-1})
fig_timeline = px.line(
    tl, x="rally_no", y="y", markers=True,
    line_shape="hv",
    title="タイムライン（U=+1, I=0, O=-1）"
)
fig_timeline.update_yaxes(tickvals=[-1,0,1], ticktext=["失点(O)","継続(I)","得点(U)"], range=[-1.1,1.1])
# I連続区間の検出→ハイライト
runs = []
current_start = None
prev_rally = None
for _, row in tl.iterrows():
    r, p = row["rally_no"], row["point_to"]
    if p == "I":
        if current_start is None:
            current_start = r
        prev_rally = r
    else:
        if current_start is not None:
            runs.append((current_start, prev_rally))
            current_start = None
if current_start is not None:
    runs.append((current_start, prev_rally))
for (start_r, end_r) in runs:
    fig_timeline.add_vrect(x0=start_r, x1=end_r, fillcolor="LightGray", opacity=0.15, line_width=0,
                           annotation_text="I（継続）", annotation_position="top left")

# ===== 画面表示（タブ）=====
tab_player, tab_skill, tab_detail, tab_timeline, tab_help = st.tabs(
    ["選手別", "スキル別", "ディテール別", "タイムライン", "説明（detailの定義）"]
)
with tab_player:
    st.plotly_chart(fig_player, use_container_width=True)
with tab_skill:
    st.plotly_chart(fig_skill, use_container_width=True)
with tab_detail:
    st.plotly_chart(fig_detail, use_container_width=True)
with tab_timeline:
    st.plotly_chart(fig_timeline, use_container_width=True)
with tab_help:
    st.subheader("detail の定義（質）")
    st.write("各スキルにおける A/B/C/M/P の意味は以下の通りです。チーム内規約に合わせて調整可能です。")
    # 見出し＋箇条書きで説明
    for code in ["S","R","D","T","A","B","F"]:
        exp = DETAIL_EXPLANATION.get(code, {})
        st.markdown(f"### {SKILL_LABELS[code]}")
        st.markdown(f"- **A**：{exp.get('A','')}")
        st.markdown(f"- **B**：{exp.get('B','')}")
        st.markdown(f"- **C**：{exp.get('C','')}")
        st.markdown(f"- **M**：{exp.get('M','（チーム内定義：ミス）')}")
        st.markdown(f"- **P**：{exp.get('P','（チーム内定義：プレッシャー下の良質）')}")
        st.divider()

st.subheader("イベント明細（5列／コード表示）")
st.dataframe(qdf, use_container_width=True)

# ===== HTML出力（縦並びレポート）=====
# 明細テーブルのHTML
df_table_html = table_to_html(qdf, "イベント明細（5列／コード表示）",
                              note="この表は画面のフィルタ適用後のデータを出力しています。")

# detail説明のHTML
help_html = "<section><h2>説明（detailの定義）</h2>" + detail_explanation_html() + "</section>"

export_html = assemble_export_html(
    kpi_vals=vals,
    fig_player=fig_player,
    fig_skill=fig_skill,
    fig_detail=fig_detail,
    fig_timeline=fig_timeline,
    df_table_html=df_table_html,
    help_html=help_html
)

st.divider()
st.download_button(
    label="📥 タブの内容を縦並びHTMLでダウンロード",
    data=export_html.encode("utf-8"),
    file_name="datavalley_report.html",
    mime="text/html"
)
