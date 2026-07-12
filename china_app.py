import streamlit as st
import hashlib
from supabase import create_client, Client

# --- Supabase接続設定 ---
SUPABASE_URL = "https://wcpxdepygveewjsqiuva.supabase.co"
SUPABASE_KEY = "sb_publishable_Sy2Saem3PgUn7S98sSGDLA_4Y2sm1SY"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
BUCKET_NAME = "audio-bucket"

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None

def login_user(username, password):
    hashed_pwd = hash_password(password)
    try:
        response = supabase.table("users").select("*").eq("username", username).execute()
        if response.data and response.data[0]["password"] == hashed_pwd:
            return True
        return False
    except Exception:
        return False

def register_user(username, password):
    hashed_pwd = hash_password(password)
    try:
        supabase.table("users").insert({"username": username, "password": hashed_pwd}).execute()
        return True
    except Exception:
        return False

# ログイン画面
if not st.session_state.logged_in:
    st.info("💡 既にアカウントがある場合は左側からログイン、初めての場合は右側からアカウントを作成してくれ。")
    col_login, col_register = st.columns(2)

    with col_login:
        st.markdown("### 🔓 ログイン")
        username = st.text_input("ユーザー名", key="login_user")
        password = st.text_input("パスワード", type='password', key="login_pwd")
        if st.button("ログインする", key="login_btn", use_container_width=True):
            if username and password and login_user(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success(f"ログイン成功だ。")
                st.rerun()  # 画面切り替え時のみ使用
            else:
                st.error("ユーザー名かパスワードが間違っているか、未入力だぞ。")

    with col_register:
        st.markdown("### 👤 アカウント新規作成")
        new_user = st.text_input("希望するユーザー名（重複不可）", key="reg_user")
        new_password = st.text_input("パスワードを設定", type='password', key="reg_pwd")
        if st.button("新しくアカウントを作る", key="register_btn", use_container_width=True):
            if new_user and new_password and register_user(new_user, new_password):
                st.success(f"アカウント【{new_user}】を作成したぞ！左側からログインしろ。")
            else:
                st.error("登録失敗、または入力漏れだ。")

# メイン画面
else:
    st.sidebar.markdown(f"**ログイン中: {st.session_state.username}**")
    if st.sidebar.button("ログアウト"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.rerun()

    tab1, tab2 = st.tabs(["🎧 リスニング・タブ", "📝 中作文・タブ"])

    # =========================================================================
    # 【🎧 1. リスニング・タブ】
    # =========================================================================
    with tab1:
        st.header("🎧 リスニング訓練とフォルダ管理")
        listening_mode = st.radio("モード選択", ["テストモード", "データ登録モード"], horizontal=True, key="list_mode_radio")

        try:
            res_fold = supabase.table("study_data").select("folder_name").eq("username", st.session_state.username).eq("type", "listening").execute()
            existing_folders = list(set([row["folder_name"] for row in res_fold.data])) if res_fold.data else []
        except Exception:
            existing_folders = []
            
        if "未分類" not in existing_folders:
            existing_folders.append("未分類")

        if listening_mode == "データ登録モード":
            st.subheader("📝 音声データの新規登録（音声は音読さんからダウンロードhttps://ondoku3.com/ja/）")
            folder_choice = st.selectbox("既存のフォルダから選ぶ", existing_folders, key="list_fold_sel")
            new_folder_input = st.text_input("または、新しいフォルダ名を入力", key="list_fold_new")
            final_folder = new_folder_input.strip() if new_folder_input.strip() else folder_choice

            st.markdown("---")
            audio_file = st.file_uploader("音声ファイルをアップロード", type=["mp3", "wav", "m4a"], key="list_audio")
            pinyin_input = st.text_input("ピンインを手入力", key="list_pinyin")
            kanji_input = st.text_input("簡体字表記を手入力", key="list_kanji")

            if st.button("リスニングデータを保存", key="list_save_btn"):
                if audio_file and pinyin_input and kanji_input:
                    audio_bytes = audio_file.read()
                    import time
                    storage_path = f"{st.session_state.username}/{int(time.time())}_{audio_file.name}"
                    
                    try:
                        supabase.storage.from_(BUCKET_NAME).upload(
                            path=storage_path,
                            file=audio_bytes,
                            file_options={"content_type": audio_file.type}
                        )
                        audio_url = supabase.storage.from_(BUCKET_NAME).get_public_url(storage_path)
                        
                        new_record = {
                            "username": st.session_state.username,
                            "type": "listening",
                            "audio_data": audio_url,
                            "pinyin": pinyin_input,
                            "kanji": kanji_input,
                            "folder_name": final_folder
                        }
                        supabase.table("study_data").insert(new_record).execute()
                        st.success(f"データをフォルダ【{final_folder}】に保存したぞ！")
                        # 登録時のみキャッシュをクリアして再読み込みさせる
                        if f"records_cache_{final_folder}" in st.session_state:
                            del st.session_state[f"records_cache_{final_folder}"]
                    except Exception as e:
                        st.error(f"保存に失敗。エラー詳細: {e}")
                else:
                    st.warning("すべての項目を入力してくれ。")

        else:
            st.subheader("🎯 リスニング・ランダムテスト")
            selected_test_folder = st.selectbox("テストするフォルダを選択しろ", existing_folders, key="list_test_fold_sel")
            
            cache_key = f"records_cache_{selected_test_folder}"
            if cache_key not in st.session_state or st.button("🔄 データを最新に更新", key="list_refresh_btn"):
                try:
                    res_records = supabase.table("study_data").select("id, audio_data, pinyin, kanji").eq("username", st.session_state.username).eq("type", "listening").eq("folder_name", selected_test_folder).execute()
                    st.session_state[cache_key] = res_records.data if res_records.data else []
                except Exception:
                    st.session_state[cache_key] = []

            records = st.session_state[cache_key]

            if not records:
                st.info(f"フォルダ【{selected_test_folder}】にはまだデータがないぞ。")
            else:
                shuffle_session_key = f"list_shuffled_{selected_test_folder}"
                if shuffle_session_key not in st.session_state or st.button("🔁 このフォルダの問題をシャッフル", key="list_shuf_btn"):
                    import random
                    shuffled_list = list(records)
                    random.shuffle(shuffled_list)
                    st.session_state[shuffle_session_key] = shuffled_list

                for index, record in enumerate(st.session_state[shuffle_session_key]):
                    rec_id = record["id"]
                    audio_url = record["audio_data"]
                    pinyin = record["pinyin"]
                    kanji = record["kanji"]
                    
                    st.markdown(f"---")
                    col1, col2 = st.columns([6, 1])
                    with col1:
                        st.write(f"**🎵 問題 {index + 1}**")
                    with col2:
                        if st.button("🗑 削除", key=f"del_list_{rec_id}"):
                            try:
                                if f"{BUCKET_NAME}/" in audio_url:
                                    storage_path = audio_url.split(f"{BUCKET_NAME}/")[-1]
                                    supabase.storage.from_(BUCKET_NAME).remove([storage_path])
                                supabase.table("study_data").delete().eq("id", rec_id).execute()
                                st.toast("削除したぞ！")
                                st.session_state[cache_key] = [r for r in st.session_state[cache_key] if r["id"] != rec_id]
                                st.session_state[shuffle_session_key] = [r for r in st.session_state[shuffle_session_key] if r["id"] != rec_id]
                            except Exception:
                                st.error("削除失敗。")
                    
                    if audio_url:
                        st.audio(audio_url, format="audio/mp3")
                    
                    # 💡 st.toggle を使って rerun なしで瞬時に答えを出し入れする
                    if st.toggle("👀 答えを見る", key=f"toggle_list_{rec_id}"):
                        st.markdown(f"**📌 ピンイン:** `{pinyin}`")
                        st.markdown(f"**🇨🇳 簡体字:** `{kanji}`")

    # =========================================================================
    # 【📝 2. 中作文・タブ】
    # =========================================================================
    with tab2:
        st.header("📝 中作文訓練（日中紐づけクイズ）")
        comp_mode = st.radio("モード選択", ["テストモード", "データ登録モード"], horizontal=True, key="comp_mode_radio")

        try:
            res_comp_fold = supabase.table("study_data").select("folder_name").eq("username", st.session_state.username).eq("type", "composition").execute()
            comp_folders = list(set([row["folder_name"] for row in res_comp_fold.data])) if res_comp_fold.data else []
        except Exception:
            comp_folders = []
            
        if "未分類" not in comp_folders:
            comp_folders.append("未分類")

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
                    new_comp = {
                        "username": st.session_state.username,
                        "type": "composition",
                        "japanese": japanese_input,
                        "kanji": kanji_input,
                        "folder_name": final_folder
                    }
                    try:
                        supabase.table("study_data").insert(new_comp).execute()
                        st.success(f"データをフォルダ【{final_folder}】に保存したぞ！")
                        if f"comp_cache_{final_folder}" in st.session_state:
                            del st.session_state[f"comp_cache_{final_folder}"]
                    except Exception:
                        st.error("データのクラウド保存に失敗したな。")
                else:
                    st.warning("日本語と中国語の両方を入力してくれ。")

        else:
            st.subheader("🎯 中作文・ランダムテスト")
            selected_test_folder = st.selectbox("テストするフォルダを選択しろ", comp_folders, key="comp_test_fold_sel")
            
            comp_cache_key = f"comp_cache_{selected_test_folder}"
            if comp_cache_key not in st.session_state or st.button("🔄 データを最新に更新", key="comp_refresh_btn"):
                try:
                    res_comp_rec = supabase.table("study_data").select("id, japanese, kanji").eq("username", st.session_state.username).eq("type", "composition").eq("folder_name", selected_test_folder).execute()
                    st.session_state[comp_cache_key] = res_comp_rec.data if res_comp_rec.data else []
                except Exception:
                    st.session_state[comp_cache_key] = []

            records = st.session_state[comp_cache_key]

            if not records:
                st.info(f"フォルダ【{selected_test_folder}】にはまだデータがないぞ。")
            else:
                comp_shuffle_key = f"comp_shuffled_{selected_test_folder}"
                if comp_shuffle_key not in st.session_state or st.button("🔁 このフォルダの問題をシャッフル", key="comp_shuf_btn"):
                    import random
                    shuffled_list = list(records)
                    random.shuffle(shuffled_list)
                    st.session_state[comp_shuffle_key] = shuffled_list

                for index, record in enumerate(st.session_state[comp_shuffle_key]):
                    rec_id = record["id"]
                    japanese = record["japanese"]
                    kanji = record["kanji"]
                    st.markdown(f"---")
                    
                    col1, col2 = st.columns([6, 1])
                    with col1:
                        st.write(f"**📝 問題 {index + 1}**")
                    with col2:
                        if st.button("🗑 削除", key=f"del_comp_{rec_id}"):
                            try:
                                supabase.table("study_data").delete().eq("id", rec_id).execute()
                                st.toast("削除したぞ！")
                                st.session_state[comp_cache_key] = [r for r in st.session_state[comp_cache_key] if r["id"] != rec_id]
                                st.session_state[comp_shuffle_key] = [r for r in st.session_state[comp_shuffle_key] if r["id"] != rec_id]
                            except Exception:
                                st.error("削除失敗。")

                    st.info(f"**日本語:** {japanese}")
                    
                    # 💡 ここも st.toggle に変更して爆速化
                    if st.toggle("👀 答えを見る", key=f"toggle_comp_{rec_id}"):
                        st.success(f"**🇨🇳 中国語:**\n{kanji}")
