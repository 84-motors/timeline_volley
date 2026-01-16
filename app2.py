
# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import re
import numpy as np

st.set_page_config(page_title="データバレーZ", layout="wide")

# --- サイドバーをブルーに変更するCSS ---
st.markdown("""
    <style>
    /* サイドバー全体の背景色 */
    [data-testid="stSidebar"] {
        background-color: #2563EB !important;  /* 明るめブルー */
    }

    /* サイドバー内の文字色 */
    [data-testid="stSidebar"] * {
        color: #ffffff !important;  /* 白 */
    }

    /* 入力欄の背景と枠 */
    [data-testid="stSidebar"] input, 
    [data-testid="stSidebar"] textarea, 
    [data-testid="stSidebar"] select {
        background-color: #ffffff !important;
        color: #000000 !important;
        border-radius: 4px;
    }

    /* チェックボックス＆マルチセレクト用の調整 */
    [data-testid="stSidebar"] .stMultiSelect > div > div {
        background-color: #ffffff !important;
        color: #000000 !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
    /* --- サイドバーの file_uploader だけ文字色を黒にする --- */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] * {
        color: #000000 !important;       /* ← 黒文字に強制 */
    }

    /* アップロードボタン（「Browse files」部分）も黒に固定 */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] .uploadedFile,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button {
        color: #000000 !important;
    }

    /* ドラッグ＆ドロップ枠内の説明文も黒に */
    [data-testid="stSidebar"] [data-testid="stFileUploader"] .upload-drop-zone {
        color: #000000 !important;
    }
    </style>
""", unsafe_allow_html=True)


REQUIRED_COLS = ["rally_no", "player", "skill", "detail", "point_to"]

# コード→ラベル
SKILL_LABELS = {
    "S": "サーブ",
    "R": "レセプション",
    "T": "トス",
    "A": "アタックヒット",
    "B": "ブロック",
    "F": "フリーボール",
    "D": "ディグ",
}

# スキル別カラー（固定）
SKILL_COLORS = {
    "サーブ": "#1f77b4",                    # S
    "レセプション": "#2ca02c",  # R
    "トス": "#ff7f0e",                      # T
    "アタックヒット": "#d62728",             # A
    "ブロック": "#9467bd",                   # B
    "フリーボール": "#8c564b", # F
    "ディグ": "#17becf"   # D
}

# （任意）スキルの表示順を固定したい場合
SKILL_ORDER = [
    "サーブ", "レセプション", "トス",
    "アタックヒット", "ブロック", "フリーボール", "ディグ"
]

POINT_LABELS = {"U": "US（自チーム）", "O": "Opponent（敵チーム）", "I": "継続（in_play）"}

# ===== detail の説明（固定文言）=====
DETAIL_EXPLANATION = {
    "S": {  # サーブの質
        "title": "サーブ(S)の質",
        "A": "相手からチャンスボールで返球、もしくは即決定（サービスエース等）。",
        "B": "相手が二段トスのスパイクで返球（攻撃簡略・品質低下）。",
        "C": "相手が通常の攻撃で返球（効果薄）。",
        "M": "サーブ側のミス（フォルト等）。",
        "P": "相手方のサーブ決定（自チームのミス以外）。",
    },
    "R": {  # レセプション（サーブカット）の質
        "title": "レセプション（R）の質",
        "A": "セッターが一歩動く程度の完璧なレシーブ（Aトス可能）。",
        "B": "セッターが動くがトスを上げられる（Bトス想定）。",
        "C": "セッターがアンダートス、もしくはセッターがトスできない（C相当）。",
        "M": "レセプションミス（ダイレクト失点・返球不能）。",
    },
    "D": {  # ディグ（スパイクレシーブ）の質
        "title": "ディグ（D）の質",
        "A": "セッターが一歩動く程度の完璧なディグ（Aトス可能）。",
        "B": "セッターが動くがトスを上げられる（Bトス想定）。",
        "C": "セッターがアンダートス、もしくはセッターがトスできない（C相当）。",
        "M": "ディグミス（ラリー中断）。",
    },
    "T": {  # トスの質
        "title": "トス(T)の質",
        "A": "完璧なトス（スパイカーが最適に打てる）。",
        "B": "トスが割れる、もしくはネットに近いがスパイカーが打てる。",
        "C": "スパイカーが打てない（返球やつなぎに切替）。",
        "M": "トスミス（ネット越え不能など）。",
    },
    "A": {  # アタックヒット（任意運用）
        "title": "アタックヒット(A)の質（チーム内定義用）",
        "A": "決定、もしくは相手を崩して次球チャンス。",
        "B": "効果あり（弱返球・チャンスボール誘発等）。",
        "C": "効果薄（通常返球）。",
        "M": "アタックミス。",
        "P": "相手方のアタック決定（自チームのミス以外）。",
    },
    "B": {  # ブロック（任意運用）
        "title": "ブロック(B)の質（チーム内定義用）",
        "A": "シャットアウト、もしくは有効タッチでチャンスへ。",
        "B": "ワンタッチ等で相手攻撃品質を下げる。",
        "C": "効果薄（通常返球）。",
        "M": "ネットタッチ等のミス。",
        "P": "相手方のブロック決定（自チームのミス以外）。",
    },
    "F": {  # フリーボール（任意運用）
        "title": "フリーボール（F:チャンス返し）の質（チーム内定義用）",
        "A": "次の組立に最適な返球。",
        "B": "やや乱れるが次を組める。",
        "C": "乱れて攻撃に移れない。",
        "M": "返球ミス。",
        "P": "相手方の決定（自チームのミス以外）。",
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
    return {"得点(U)": pts, "失点(O)": lost}

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


def assemble_export_html(
    kpi_vals,
    #fig_player_points,
    fig_player_points_stacked,
    #fig_player_losses,
    fig_player_losses_stacked,
    fig_skill,
    fig_skill_detail,
    fig_timeline,
    df_table_html,
    help_html,
    fig_sunburst=None,
    report_date=None,
    report_opponent=""
):
    head = """

<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>データバレー レポート</title>
<!-- Plotly をCDNから1回だけ読み込み -->
<script src="https://cdn.plot.ly/plotly-2.30.0.min.js"></script>
<style>
  body { font-family: system-ui, -apple-system, 'Segoe UI', Roboto, 'Noto Sans JP', sans-serif; margin: 24px; }
  h1 { margin: 0 0 8px 0; }
  h2 { margin: 24px 0 8px; border-left: 6px solid #3b82f6; padding-left: 8px; }
  section { margin-bottom: 24px; }
  table.kpi { border-collapse: collapse; margin-top: 4px; }
  table.kpi th { text-align:left; padding: 6px 10px; background:#f3f4f6; }
  table.kpi td { padding: 6px 10px; }
  table.dataframe { border-collapse: collapse; width: 100%; }
  table.dataframe th, table.dataframe td { border: 1px solid #e5e7eb; padding: 6px 10px; }
</style>
</head><body>
<h1>レポート</h1>
"""
    
    # NEW: 試合情報の見出し（YYYY/MM/DD vs 相手）
    date_str = (report_date.strftime("%Y/%m/%d") if isinstance(report_date, datetime.date) else "")
    opp_str = report_opponent or ""
    header_html = f"<h1>データバレー レポート</h1><p><strong>{date_str}</strong> vs <strong>{opp_str}</strong></p>"

    body = (
        header_html +
        kpi_to_html(kpi_vals) +
        fig_to_html(fig_timeline, "タイムライン") +
        fig_to_html(fig_player_points_stacked, "選手別 × スキル別 得点数積み上げ") +
        fig_to_html(fig_player_losses_stacked, "選手別 × スキル別 失点数積み上げ") +
        fig_to_html(fig_skill,  "スキル別 得点数") +
        fig_to_html(fig_skill_detail, "スキル別 × ディテール（質）件数") +
        help_html +
        df_table_html
    )
    tail = "</body></html>"
    return head + body + tail


st.title("🏐 データバレーZ")


# --- 画面上部：試合情報入力（日付・対戦相手） ---

st.markdown("### 試合情報")
col_d, col_o = st.columns([1, 2])  # 左：日付、右：相手
with col_d:
    match_date = st.date_input("日付", value=datetime.date.today())
with col_o:
    opponent = st.text_input("対戦相手（例：〇〇クラブ）", value="")

def _sanitize_filename(name: str) -> str:
    # Windows等で不正な文字を避ける
    return re.sub(r'[\\/:*?"<>|]+', '_', name.strip())

def _date_yyyymmdd(d: datetime.date) -> str:
    return d.strftime("%Y%m%d") if isinstance(d, datetime.date) else "00000000"

# ファイル名の候補（未入力時の安全対策込み）
safe_opponent = _sanitize_filename(opponent) if opponent else "opponent"
file_stub = f"{_date_yyyymmdd(match_date)}_{safe_opponent}"

# --- サイドバー：データ ---
with st.sidebar:
    st.header("データ")
    uploaded = st.file_uploader("CSVをアップロード", type=["csv"])
    use_sample = st.checkbox("サンプル（20260112新人戦_日下ブラック1セット目.csv）を使う", value=True)
    if uploaded:
        df = load_data(uploaded)
    elif use_sample:
        df = load_data("data/20260112新人戦_日下ブラック1セット目.csv")
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

def _to_player_no(val):
    # 'No.1', 'NO1', '1' などから数字のみ抽出。取れない場合はNaN
    s = str(val)
    m = re.search(r'(\d+)', s)
    return int(m.group(1)) if m else np.nan

qdf["player_no"] = qdf["player"].apply(_to_player_no)

def _display_name(no):
    if pd.isna(no):
        return str(no)
    no = int(no)
    # 入力欄で指定された名前があればそれを優先、なければ "No{n}"
    name = st.session_state.get(f"player_name_{no}", "")
    return name.strip() if isinstance(name, str) and name.strip() else f"No{no}"

qdf["player_display"] = qdf["player_no"].apply(_display_name)

# グラフ用の並び順（番号昇順→表示名）
PLAYER_ORDER_LABELS = (
    qdf.dropna(subset=["player_no"])
       .sort_values("player_no")[["player_no", "player_display"]]
       .drop_duplicates()["player_display"]
       .tolist()
)

# KPI
vals = kpi(qdf)
col1, col2, col3, col4 = st.columns(4)
for col, (k,v) in zip([col1,col2,col3,col4], vals.items()):
    col.metric(k, v)

st.divider()


# --- 画面上部：選手名入力欄（player_no → 名前） ---
st.markdown("### 選手名（player番号 → 名前）")

# デフォルトは No1〜No6 を表示
DEFAULT_PLAYER_COUNT = 6

# セッションに保存（Streamlit 再描画対策）
if "player_name_count" not in st.session_state:
    st.session_state.player_name_count = DEFAULT_PLAYER_COUNT

# 追加ボタン（最大 No12）
col_left, col_right = st.columns([4, 1])
with col_right:
    if st.button("＋ 選手を追加", help="No7 以降を追加します（最大 No12）"):
        if st.session_state.player_name_count < 12:
            st.session_state.player_name_count += 1

# 入力欄（No1 → No{count}）
player_names = {}
with col_left:
    for i in range(1, st.session_state.player_name_count + 1):
        key = f"player_name_{i}"
        default_label = f"No.{i}"
        player_names[i] = st.text_input(f"No{i} の名前", value="", key=key)


# ===== 可視化用の図（レポート出力でも再利用）=====

# ラベル化用にコピー
qs = qdf.copy()
qs["skill_label"] = qs["skill"].map(SKILL_LABELS)

# --- 1) 選手別・得点（Uカウント） ---

gp_points = qdf.groupby("player_display")["point_to"] \
               .apply(lambda s: (s == "U").sum()).reset_index(name="points_U")

fig_player_points = px.bar(
    gp_points, x="player_display", y="points_U",
    title="選手別 得点数（U）",
    labels={"points_U": "得点数（U）", "player_display": "選手"},
    category_orders={"player_display": PLAYER_ORDER_LABELS}
)



# --- 2) 選手別 × スキル別・得点（U）積み上げ ---
qs = qdf.copy()
qs["skill_label"] = qs["skill"].map(SKILL_LABELS)
udf = qs[qs["point_to"] == "U"].copy()

gp_points_stacked = udf.groupby(["player_display", "skill_label"]) \
                       .size().reset_index(name="count")

fig_player_points_stacked = px.bar(
    gp_points_stacked, x="player_display", y="count",
    color="skill_label", barmode="stack",
    title="選手別 × スキル別 得点数（U）積み上げ",
    labels={"count": "得点数（U）", "player_display": "選手", "skill_label": "スキル"},
    color_discrete_map=SKILL_COLORS,
    category_orders={"player_display": PLAYER_ORDER_LABELS, "skill_label": SKILL_ORDER}
)
fig_player_points_stacked.update_layout(legend_title_text="スキル")



# --- 3) 選手別・失点（Oカウント） ---
gp_losses = qdf.groupby("player_display")["point_to"] \
               .apply(lambda s: (s == "O").sum()).reset_index(name="points_O")

fig_player_losses = px.bar(
    gp_losses, x="player_display", y="points_O",
    title="選手別 失点数（O）",
    labels={"points_O": "失点数（O）", "player_display": "選手"},
    category_orders={"player_display": PLAYER_ORDER_LABELS}
)



# --- 4) 選手別 × スキル別・失点（O）積み上げ ---
odf = qs[qs["point_to"] == "O"].copy()
gp_losses_stacked = odf.groupby(["player_display", "skill_label"]) \
                       .size().reset_index(name="count")

fig_player_losses_stacked = px.bar(
    gp_losses_stacked, x="player_display", y="count",
    color="skill_label", barmode="stack",
    title="選手別 × スキル別 失点数（O）積み上げ",
    labels={"count": "失点数（O）", "player_display": "選手", "skill_label": "スキル"},
    color_discrete_map=SKILL_COLORS,
    category_orders={"player_display": PLAYER_ORDER_LABELS, "skill_label": SKILL_ORDER}
)
fig_player_losses_stacked.update_layout(legend_title_text="スキル")



# --- 既存：スキル別／ディテール別 ---
gs = qs.groupby("skill_label")["point_to"].apply(lambda s: (s == "U").sum()).reset_index(name="points_U")
fig_skill = px.bar(gs, x="skill_label", y="points_U", title="スキル別 得点数（U）",
                   labels={"points_U": "得点数（U）", "skill_label": "スキル"})

# --- NEW: スキル別 × ディテール（質）の積み上げ棒グラフ ---
# qdf はフィルタ適用後のデータ
qd = qdf.copy()
qd["skill_label"] = qd["skill"].map(SKILL_LABELS)

# スキル × detail ごとの件数
gs_detail = qd.groupby(["skill_label", "detail"]).size().reset_index(name="count")

# detail の表示順（A/B/C/M/P）を固定（任意）
DETAIL_ORDER = ["A", "B", "C", "M", "P"]

fig_skill_detail = px.bar(
    gs_detail,
    x="skill_label",
    y="count",
    color="detail",           # ← 質コードで色分け
    barmode="stack",
    title="スキル別 × ディテール（質）件数",
    labels={"skill_label": "スキル", "count": "件数", "detail": "質"},
    category_orders={"detail": DETAIL_ORDER}
)

# （任意）色の固定：A/B/C/M/P の配色ルールがあれば指定
DETAIL_COLORS = {"A":"#1f77b4","B":"#2ca09a","C":"#ffef0e","M":"#d62728","P":"#9467bd"}
fig_skill_detail.update_layout(legend_title_text="質（detail）")
fig_skill_detail.for_each_trace(lambda t: t.update(marker_color=DETAIL_COLORS.get(t.name, t.marker.color)))


# --- NEW: Sunburst（内=player / 中=skill / 外=detail）---
sb = qdf.copy()

# スキルの日本語ラベル列
sb["skill_label"] = sb["skill"].map(SKILL_LABELS)

# 件数（イベント数）を value に使うために全行を1とする列を用意
sb["count"] = 1

# Sunburst作成
fig_sunburst = px.sunburst(
    sb,
    path=["player_display", "skill_label", "detail"],   # ← 内周が名前に
    values="count",
    title="選手別ボール関与構造（選手名 → スキル → ディテール）",
    color="detail",
    color_discrete_map=DETAIL_COLORS
)
fig_sunburst.update_traces(
    hovertemplate="層: %{label}<br>件数: %{value}<br>割合: %{percentRoot:.1%}"
)


# ホバー表示の改善（選手・スキル・質・件数）
fig_sunburst.update_traces(
    hovertemplate=(
        "層: %{label}<br>"
        "件数: %{value}<br>"
        "割合: %{percentRoot:.1%}<extra></extra>"
    )
)

# Sunburst サイズ拡大（大きめに表示）
fig_sunburst.update_layout(
    width=900,    # 横幅 900px（必要なら 1000〜1200 に拡大可）
    height=900,   # 高さ 900px（必要なら 1000 以上もOK）
    margin=dict(t=80, l=10, r=10, b=10)
)

# --- タイムライン ---

# --- タイムライン（U と O のみ。I は除外） ---
tl = qdf[qdf["point_to"].isin(["U", "O"])].copy()
tl = tl.sort_values("rally_no")

# 数値へ変換：U=+1、O=-1
tl["y"] = tl["point_to"].map({"U": 1, "O": -1})

fig_timeline = px.line(
    tl,
    x="rally_no",
    y="y",
    markers=True,
    line_shape="linear",
    title="タイムライン（得点=+1 / 失点=-1）",
    labels={"rally_no": "ラリー番号", "y": "結果"}
)

fig_timeline.update_traces(marker=dict(size=12))  # ★ マーカーを4倍サイズに

fig_timeline.update_yaxes(
    tickvals=[-1, 1],
    ticktext=["失点(O)", "得点(U)"],
    range=[-1.5, 1.5]
)



# I連続区間の検出→ハイライト
runs, current_start, prev_rally = [], None, None
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
tab_timeline, tab_player, tab_skill, tab_help = st.tabs(
    ["タイムライン", "選手別", "スキル別", "説明やデータ作成手順など"]
)
with tab_timeline:
    st.plotly_chart(fig_timeline, use_container_width=True)
with tab_player:
    #st.plotly_chart(fig_player_points, use_container_width=True)
    st.plotly_chart(fig_player_points_stacked, use_container_width=True)
    #st.plotly_chart(fig_player_losses, use_container_width=True)
    st.plotly_chart(fig_player_losses_stacked, use_container_width=True)
    st.plotly_chart(fig_sunburst, use_container_width=True)

with tab_skill:
    st.plotly_chart(fig_skill, use_container_width=True)
    st.plotly_chart(fig_skill_detail, use_container_width=True)
with tab_help:
    st.subheader("スキルの定義")
    st.markdown("""
- **S：サーブ**  
- **R：レセプション（サーブカット）**  
- **D：ディグ（スパイクレシーブ等、相手方からの返球に対するファーストレシーブ）**  
- **A：アタックヒット**  
- **B：ブロック**  
- **F：フリーボール（チャンスボールなど相手方への返球）**  
    """)

    st.divider()

    st.subheader("ディテールの定義（質）")
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

# 明細テーブルは player_display を表示し、列名も「player（選手名）」に統一
table_df = qdf[["rally_no", "player_display", "skill", "detail", "point_to"]].copy()
table_df = table_df.rename(columns={"player_display": "player"})

st.subheader("イベント明細（選手名表示）")
st.dataframe(table_df, use_container_width=True)


# ===== HTML出力（縦並びレポート）=====
# 明細テーブルのHTML
df_table_html = table_to_html(
    table_df,
    "イベント明細（選手名表示）",
    note="この表は画面のフィルタ適用後データを、player を選手名で表示しています。"
)


# detail説明のHTML
help_html = "<section><h2>説明・入力方法など</h2>" + detail_explanation_html() + "</section>"

export_html = assemble_export_html(
    kpi_vals=vals,
    #fig_player_points=fig_player_points,
    fig_player_points_stacked=fig_player_points_stacked,
    #fig_player_losses=fig_player_losses,
    fig_player_losses_stacked=fig_player_losses_stacked,
    fig_sunburst=fig_sunburst,
    fig_skill=fig_skill,
    fig_skill_detail=fig_skill_detail,
    fig_timeline=fig_timeline,
    df_table_html=df_table_html,
    help_html=help_html,
    report_date=match_date,
    report_opponent=opponent
)


st.divider()
st.download_button(
    label="📥 タブの内容を縦並びHTMLでダウンロード",
    data=export_html.encode("utf-8"),
    file_name=f"{file_stub}.html",
    mime="text/html"
)

