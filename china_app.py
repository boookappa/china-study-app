import streamlit as st
import sqlite3
import hashlib

# 1. データベースの初期設定
def init_db():
    conn = sqlite3.connect('china_study.db', check_same_thread=False)
    c = conn.cursor()
    # ユーザー管理テーブル
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY, 
            password TEXT
        )
    ''')
    # 学習データ管理テーブル
    c.execute('''
        CREATE TABLE IF NOT EXISTS study_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            type TEXT,        -- 'listening' または 'composition'
            audio_data BLOB,  -- 音声のバイナリデータ
            pinyin TEXT,
            kanji TEXT,
            japanese TEXT,
            folder_name TEXT DEFAULT '未分類'
        )
    ''')
    conn.commit()
    return conn

conn = init_db()
c = conn.cursor()

# パスワードを暗号化（ハッシュ化）する関数
def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# セッション状態（ログイン状態）の初期化
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""

# --- 画面の構築 ---
st.title("🇨🇳 中国語学習マスターアプリ")

# ログインしていない場合の画面
if not st.session_state.logged_in:
    st.info("💡 既にアカウントがある場合は左側からログイン、初めての場合は右側からアカウントを作成してくれ。")
    
    # 画面を綺麗に2つに分割する
    col_login, col_register = st.columns(2)

    # --- 左側：ログインエリア ---
    with col_login:
        st.markdown("### 🔓 ログイン")
        username = st.text_input("ユーザー名", key="login_user")
        password = st.text_input("パスワード", type='password', key="login_pwd")
        
        if st.button("ログインする", key="login_btn", use_container_width=True):
            if username and password:
                hashed_pwd = hash_password(password)
                c.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, hashed_pwd))
                result = c.fetchone()
                
                if result:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.success(f"ログイン成功だ。ようこそ、{username}！")
                    st.rerun()
                else:
                    st.error("ユーザー名かパスワードが間違っているぞ。")
            else:
                st.warning("ユーザー名とパスワードを入力してくれ。")

    # --- 右側：アカウント作成エリア ---
    with col_register:
        st.markdown("### 👤 アカウント新規作成")
        new_user = st.text_input("希望するユーザー名（重複不可）", key="reg_user")
        new_password = st.text_input("パスワードを設定", type='password', key="reg_pwd")
        
        if st.button("新しくアカウントを作る", key="register_btn", use_container_width=True):
            if new_user and new_password:
                hashed_pwd = hash_password(new_password)
                try:
                    c.execute('INSERT INTO users (username, password) VALUES (?,?)', (new_user, hashed_pwd))
                    conn.commit()
                    st.success(f"アカウント【{new_user}】を作成したぞ！左側のログインから入るんだ。")
                except sqlite3.IntegrityError:
                    st.error("そのユーザー名は既に使われているぞ。別の名前にしろ。")
            else:
                st.warning("登録するユーザー名とパスワードを入力してくれ。")

# ログインに成功した場合のメイン画面
else:
    st.sidebar.markdown(f"**ログイン中: {st.session_state.username}**")
    if st.sidebar.button("ログアウト"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

    # 機能別のタブを作成
    tab1, tab2 = st.tabs(["🎧 リスニング・タブ", "📝 中作文・タブ"])

    # =========================================================================
    # 【🎧 1. リスニング・タブ】
    # =========================================================================
    with tab1:
        st.header("🎧 リスニング訓練とフォルダ管理")
        listening_mode = st.radio("モード選択", ["テストモード", "データ登録モード"], horizontal=True, key="list_mode_radio")

        # 既存フォルダ名一覧の取得
        c.execute("SELECT DISTINCT folder_name FROM study_data WHERE username = ? AND type = 'listening'", (st.session_state.username,))
        existing_folders = [row[0] for row in c.fetchall()]
        if "未分類" not in existing_folders:
            existing_folders.append("未分類")

        # 【データ登録モード】
        if listening_mode == "データ登録モード":
            st.subheader("📝 音声データの新規登録")
            folder_choice = st.selectbox("既存のフォルダから選ぶ", existing_folders, key="list_fold_sel")
            new_folder_input = st.text_input("または、新しいフォルダ名を入力", key="list_fold_new")
            final_folder = new_folder_input.strip() if new_folder_input.strip() else folder_choice

            st.markdown("---")
            audio_file = st.file_uploader("音声ファイルをアップロード（mp3, wavなど）", type=["mp3", "wav", "m4a"], key="list_audio")
            pinyin_input = st.text_input("ピンインを手入力", key="list_pinyin")
            kanji_input = st.text_input("簡体字表記を手入力", key="list_kanji")

            if st.button("リスニングデータを保存", key="list_save_btn"):
                if audio_file and pinyin_input and kanji_input:
                    audio_bytes = audio_file.read()
                    c.execute('''
                        INSERT INTO study_data (username, type, audio_data, pinyin, kanji, folder_name)
                        VALUES (?, 'listening', ?, ?, ?, ?)
                    ''', (st.session_state.username, audio_bytes, pinyin_input, kanji_input, final_folder))
                    conn.commit()
                    st.success(f"データをフォルダ【{final_folder}】に保存したぞ！")
                    st.rerun()
                else:
                    st.warning("すべての項目を入力してくれ。")

        # 【テストモード】
        else:
            st.subheader("🎯 リスニング・ランダムテスト")
            selected_test_folder = st.selectbox("テストするフォルダを選択しろ", existing_folders, key="list_test_fold_sel")
            
            c.execute('''
                SELECT id, audio_data, pinyin, kanji 
                FROM study_data 
                WHERE username = ? AND type = 'listening' AND folder_name = ?
            ''', (st.session_state.username, selected_test_folder))
            records = c.fetchall()

            if not records:
                st.info(f"フォルダ【{selected_test_folder}】にはまだデータがないぞ。")
            else:
                shuffle_session_key = f"list_shuffled_{selected_test_folder}"
                if shuffle_session_key not in st.session_state or st.button("🔁 このフォルダの問題をシャッフル", key="list_shuf_btn"):
                    import random
                    shuffled_list = list(records)
                    random.shuffle(shuffled_list)
                    st.session_state[shuffle_session_key] = shuffled_list
                    st.rerun()

                for index, record in enumerate(st.session_state[shuffle_session_key]):
                    rec_id, audio_bytes, pinyin, kanji = record
                    st.markdown(f"---")
                    
                    # レイアウトを整えるため列を分ける（問題番号と削除ボタン）
                    col1, col2 = st.columns([6, 1])
                    with col1:
                        st.write(f"**🎵 問題 {index + 1}**")
                    with col2:
                        if st.button("🗑 削除", key=f"del_list_{rec_id}"):
                            c.execute("DELETE FROM study_data WHERE id = ?", (rec_id,))
                            conn.commit()
                            st.toast("データを削除したぞ！")
                            st.session_state[shuffle_session_key] = [r for r in st.session_state[shuffle_session_key] if r[0] != rec_id]
                            st.rerun()
                    
                    st.audio(audio_bytes, format="audio/mp3")
                    
                    show_ans_key = f"show_ans_listening_{rec_id}"
                    if show_ans_key not in st.session_state:
                        st.session_state[show_ans_key] = False

                    if not st.session_state[show_ans_key]:
                        if st.button("👀 答えを見る", key=f"btn_show_{rec_id}"):
                            st.session_state[show_ans_key] = True
                            st.rerun()
                    else:
                        st.markdown(f"**📌 ピンイン:** `{pinyin}`")
                        st.markdown(f"**🇨🇳 簡体字:** `{kanji}`")
                        if st.button("🙈 答えを隠す", key=f"btn_hide_{rec_id}"):
                            st.session_state[show_ans_key] = False
                            st.rerun()

    # =========================================================================
    # 【📝 2. 中作文・タブ】
    # =========================================================================
    with tab2:
        st.header("📝 中作文訓練（日中紐づけクイズ）")
        comp_mode = st.radio("モード選択", ["テストモード", "データ登録モード"], horizontal=True, key="comp_mode_radio")

        # 既存フォルダ名一覧の取得
        c.execute("SELECT DISTINCT folder_name FROM study_data WHERE username = ? AND type = 'composition'", (st.session_state.username,))
        comp_folders = [row[0] for row in c.fetchall()]
        if "未分類" not in comp_folders:
            comp_folders.append("未分類")

        # 【データ登録モード】
        if comp_mode == "データ登録モード":
            st.subheader("📝 中作文データの新規登録")
            folder_choice = st.selectbox("既存のフォルダから選ぶ", comp_folders, key="comp_fold_sel")
            new_folder_input = st.text_input("または、新しいフォルダ名を入力", key="comp_fold_new")
            final_folder = new_folder_input.strip() if new_folder_input.strip() else folder_choice

            st.markdown("---")
            japanese_input = st.text_area("日本語の文章を手入力（問題）", key="comp_jap")
            kanji_input = st.text_area("中国語の文章（簡体字・ピンインなど）を手入力（解答）", key="comp_kanji")

            if st.button("中作文データを保存", key="comp_save_btn"):
                if japanese_input and kanji_input:
                    c.execute('''
                        INSERT INTO study_data (username, type, japanese, kanji, folder_name)
                        VALUES (?, 'composition', ?, ?, ?)
                    ''', (st.session_state.username, japanese_input, kanji_input, final_folder))
                    conn.commit()
                    st.success(f"データをフォルダ【{final_folder}】に保存したぞ！")
                    st.rerun()
                else:
                    st.warning("日本語と中国語の両方を入力してくれ。")

        # 【テストモード】
        else:
            st.subheader("🎯 中作文・ランダムテスト")
            selected_test_folder = st.selectbox("テストするフォルダを選択しろ", comp_folders, key="comp_test_fold_sel")
            
            c.execute('''
                SELECT id, japanese, kanji 
                FROM study_data 
                WHERE username = ? AND type = 'composition' AND folder_name = ?
            ''', (st.session_state.username, selected_test_folder))
            records = c.fetchall()

            if not records:
                st.info(f"フォルダ【{selected_test_folder}】にはまだデータがないぞ。")
            else:
                shuffle_session_key = f"comp_shuffled_{selected_test_folder}"
                if shuffle_session_key not in st.session_state or st.button("🔁 このフォルダの問題をシャッフル", key="comp_shuf_btn"):
                    import random
                    shuffled_list = list(records)
                    random.shuffle(shuffled_list)
                    st.session_state[shuffle_session_key] = shuffled_list
                    st.rerun()

                for index, record in enumerate(st.session_state[shuffle_session_key]):
                    rec_id, japanese, kanji = record
                    st.markdown(f"---")
                    
                    col1, col2 = st.columns([6, 1])
                    with col1:
                        st.write(f"**📝 問題 {index + 1}**")
                    with col2:
                        if st.button("🗑 削除", key=f"del_comp_{rec_id}"):
                            c.execute("DELETE FROM study_data WHERE id = ?", (rec_id,))
                            conn.commit()
                            st.toast("データを削除したぞ！")
                            st.session_state[shuffle_session_key] = [r for r in st.session_state[shuffle_session_key] if r[0] != rec_id]
                            st.rerun()

                    st.info(f"**日本語:** {japanese}")
                    
                    show_ans_key = f"show_ans_comp_{rec_id}"
                    if show_ans_key not in st.session_state:
                        st.session_state[show_ans_key] = False

                    if not st.session_state[show_ans_key]:
                        if st.button("👀 答えを見る", key=f"btn_show_comp_{rec_id}"):
                            st.session_state[show_ans_key] = True
                            st.rerun()
                    else:
                        st.success(f"**🇨🇳 中国語:**\n{kanji}")
                        if st.button("🙈 答えを隠す", key=f"btn_hide_comp_{rec_id}"):
                            st.session_state[show_ans_key] = False
                            st.rerun()