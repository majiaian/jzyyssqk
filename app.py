# app.py
import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title='切口分类比例计算器', layout='centered')
st.title('📊 切口分类比例计算器')
st.info('上传“待处理.xlsx”，系统依据“对照表.xlsx”计算（手术编码+诊断名称）对应的切口类别占比，'
        '输出格式：单一 100% 仅显示类别，其余显示比例。行顺序保持不变。')

# ---------- 1. 读取本地对照表 ----------
@st.cache_data
def load_ref():
    try:
        return pd.read_excel('对照表.xlsx',
                             usecols=['手术编码', '诊断名称', '切口类别'])
    except FileNotFoundError:
        st.error('服务器缺少“对照表.xlsx”，请将其放在同目录后重试！')
        st.stop()

ref = load_ref()

# ---------- 2. 构造比例映射 ----------
def build_map(df):
    cnt = (df.assign(切口类别=lambda d:d['切口类别'].astype(int))
             .dropna(subset=['切口类别'])
             .groupby(['手术编码', '诊断名称', '切口类别'])
             .size().reset_index(name='n'))
    cnt['pct'] = (cnt.groupby(['手术编码', '诊断名称'])['n']
                    .transform(lambda x: (x / x.sum() * 100).round(0).astype(int)))
    # 100% 只保留类别，其余保留比例
    cnt['txt'] = cnt.apply(lambda r: f"{r['切口类别']}" if r['pct'] == 100
                           else f"{r['切口类别']}:{r['pct']}%", axis=1)
    return cnt.groupby(['手术编码', '诊断名称'])['txt'].agg(','.join).rename('切口类别比例')

ratio_map = build_map(ref)

# ---------- 3. 上传 & 处理 ----------
uploaded = st.file_uploader('请上传“待处理.xlsx”', type=['xlsx'])
if uploaded:
    df_input = pd.read_excel(uploaded)
    # left 合并保证行顺序不变
    df_out = df_input.merge(ratio_map, on=['手术编码', '诊断名称'], how='left')

    # ---------- 4. 下载 ----------
    def to_excel(df):
        bio = BytesIO()
        with pd.ExcelWriter(bio, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        bio.seek(0)
        return bio.getvalue()

    st.success('处理完成！')
    st.download_button(
        label='⬇ 下载 切口分类.xlsx',
        data=to_excel(df_out),
        file_name='切口分类.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
