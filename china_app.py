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
    st.info("💡 既にアカウントがある場合は左側からログイン、初めての場合は右側からアカウントを作成しろ。ユーザー名「nao7」（パスワード「123」）にはすでにいくつかのデータが入っているので自由に使ってもらっていいです。ただしデータは消さないでね。「nao7」のパスワードも変えないでね")
    col_login, col_register = st.columns(2)

    with col_login:
        st.markdown("### 🔓 ログイン")
        username = st.text_input("ユーザー名", key="login_user")
        password = st.text_input("パスワード", type='password', key="login_pwd")
        if st.button("ログインする", key="login_btn", use_container_width=True):
            if username and password and login_user(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success(f"ログイン成功。")
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
    with st.sidebar.expander("🔑 パスワードを変更"):
        old_pw = st.text_input("現在のパスワード", type="password", key="old_pw")
        new_pw = st.text_input("新しいパスワード", type="password", key="new_pw")
        
        if st.button("パスワードを変更する", key="change_pw_btn"):
            if old_pw and new_pw:
                # 既存の login_user を使って認証
                if login_user(st.session_state.username, old_pw):
                    try:
                        new_hashed = hash_password(new_pw)
                        supabase.table("users")\
                            .update({"password": new_hashed})\
                            .eq("username", st.session_state.username)\
                            .execute()
                        st.success("パスワードを変更したぞ！")
                    except Exception as e:
                        st.error(f"変更失敗: {e}")
                else:
                    st.error("現在のパスワードが間違っているぞ。")
            else:
                st.warning("両方入力しろ。")
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

        # フォルダ一覧取得はモードに関わらず共通
        try:
            res_fold = supabase.table("study_data").select("folder_name").eq("username", st.session_state.username).eq("type", "listening").execute()
            existing_folders = list(set([row["folder_name"] for row in res_fold.data])) if res_fold.data else []
        except Exception:
            existing_folders = []
            
        if "未分類" not in existing_folders:
            existing_folders.append("未分類")
        import re
        def natural_sort_key(s):
            return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]
        
        existing_folders.sort(key=natural_sort_key)

        # --- ここからモード別の分岐 ---
        if listening_mode == "データ登録モード":
            # 1. フォルダ管理エリア

            # --- データ登録モード内のフォルダ管理エリアへ追加 ---
            with st.expander("🗑️ フォルダを削除する"):
                del_folder = st.selectbox("削除したいフォルダを選択", existing_folders, key="del_folder_sel")
                if st.button("フォルダを削除", key="delete_folder_btn"):
                # "未分類"は消せないようにガードしておく
                    if del_folder == "未分類":
                        st.warning("【未分類】は消せないぞ。")
                    else:
                        try:
                        # 該当フォルダの全データを一括削除
                            supabase.table("study_data")\
                                .delete()\
                                .eq("username", st.session_state.username)\
                                .eq("folder_name", del_folder)\
                                .execute()
                            st.success(f"【{del_folder}】をフォルダごと削除したぞ！")
                            st.rerun()
                        except Exception as e:
                            st.error(f"削除失敗だ: {e}")
            with st.expander("📁 フォルダ名を変更する"):
                old_name = st.selectbox("変更したいフォルダを選択", existing_folders, key="rename_old_list")
                new_name = st.text_input("新しいフォルダ名を入力", key="rename_new_list")
                if st.button("フォルダ名を変更する", key="rename_btn_list"):
                    if old_name and new_name.strip():
                        try:
                            supabase.table("study_data").update({"folder_name": new_name.strip()})\
                                .eq("username", st.session_state.username).eq("folder_name", old_name).execute()
                            st.success(f"【{old_name}】を【{new_name.strip()}】に変更したぞ！")
                            st.rerun()
                        except Exception as e:
                            st.error(f"変更失敗だ: {e}")
                    else:
                        st.warning("名前を入力しろ。")

            with st.container(border=True):
                st.subheader("📁 フォルダの新規作成")
                new_folder_input = st.text_input("新しいフォルダ名を入力", key="list_fold_new")
                if st.button("フォルダを作成", key="create_fold_btn"):
                    if new_folder_input.strip():
                        try:
                            supabase.table("study_data").insert({"username": st.session_state.username, "type": "listening", "folder_name": new_folder_input.strip(), "japanese": "（ダミーデータ）"}).execute()
                            st.success(f"【{new_folder_input}】を作成したぞ！")
                            st.rerun() 
                        except Exception as e:
                            st.error(f"作成失敗だ: {e}")
                    else:
                        st.warning("名前を入力しろ。")

            # 2. データ登録エリア
            st.subheader("📝 音声データの新規登録（音声は、音読さんで中国語を入力して、xiaoxiaoで読ませてダウンロードし、下でアップロードしてください　https://ondoku3.com/ja/　）")
            folder_choice = st.selectbox("既存のフォルダから選ぶ", existing_folders, key="list_fold_sel")
            audio_file = st.file_uploader("音声ファイルをアップロード", type=["mp3", "wav", "m4a"], key="list_audio")
            pinyin_input = st.text_input("ピンインを手入力", key="list_pinyin")
            kanji_input = st.text_input("簡体字表記を手入力", key="list_kanji")

            # --- 登録処理 ---
            # --- 登録処理の修正 ---
            if st.button("リスニングデータを保存", key="list_save_btn"):
                if audio_file and pinyin_input and kanji_input:
                    import time # ファイル名の重複を防ぐために時間を足す
                    try:
                    # ファイル名にタイムスタンプを付加する
                        timestamp = int(time.time())
                        unique_filename = f"{timestamp}_{audio_file.name}"
                        storage_path = f"listening/{st.session_state.username}/{unique_filename}"
                    
                    # アップロード実行
                        supabase.storage.from_(BUCKET_NAME).upload(
                            path=storage_path, 
                            file=audio_file.getvalue(),
                            file_options={"content-type": audio_file.type}
                        )
                    
                    # 以降の処理はさっきの通り…
                    # 2. 公開URLを取得
                        res_url = supabase.storage.from_(BUCKET_NAME).get_public_url(storage_path)
                        audio_url = res_url
                    
                    # 3. DBへ本物のURLを登録
                        supabase.table("study_data").insert({
                            "username": st.session_state.username,
                            "type": "listening",
                            "folder_name": folder_choice,
                            "audio_data": audio_url, # ここをURLにする！
                            "pinyin": pinyin_input,
                            "kanji": kanji_input
                        }).execute()
                    
                        st.success(f"【{folder_choice}】に保存したぞ！")
                        st.rerun()
                    except Exception as e:
                        st.error(f"保存失敗だ: {e}")

        elif listening_mode == "テストモード":
            st.subheader("🎯 リスニング・ランダムテスト")
            selected_test_folder = st.selectbox("テストするフォルダを選択しろ", existing_folders, key="list_test_fold_sel")
            
            cache_key = f"records_cache_{selected_test_folder}"
            if cache_key not in st.session_state or st.button("🔄 データを最新に更新（反映されない場合は下のシャッフルを押すと上手くいくと思います）", key="list_refresh_btn"):
                # 変数をtryの外で定義しておく
                raw_data = [] 
                try:
                    res_records = supabase.table("study_data")\
                        .select("id, audio_data, pinyin, kanji")\
                        .eq("username", st.session_state.username)\
                        .eq("type", "listening")\
                        .eq("folder_name", selected_test_folder)\
                        .execute()
                    
                    raw_data = res_records.data if res_records.data else []
                    #st.write("DEBUG: 取得した生データ:", raw_data) # 確認用
                except Exception as e:
                    st.error(f"取得エラー: {e}")
                
                # 取得したデータをセッションに保存
                st.session_state[cache_key] = raw_data

            records = st.session_state.get(cache_key, [])
            
            if not records:
                st.info(f"フォルダ【{selected_test_folder}】にはまだデータがないぞ。")
            else:
                # シャッフルと表示処理
                shuffle_session_key = f"list_shuffled_{selected_test_folder}"
                
                # リセット用のキーを管理
                expander_reset_key = f"expander_reset_{selected_test_folder}"
                if expander_reset_key not in st.session_state:
                    st.session_state[expander_reset_key] = 0

                if shuffle_session_key not in st.session_state or st.button("🔁 このフォルダの問題をシャッフル", key="list_shuf_btn"):
                    import random
                    shuffled_list = list(records)
                    random.shuffle(shuffled_list)
                    st.session_state[shuffle_session_key] = shuffled_list
                    st.session_state[expander_reset_key] += 1
                    st.rerun()

                # ★ここで valid_records を必ず定義する！
                valid_records = [r for r in st.session_state[shuffle_session_key] if r.get("audio_data") and r.get("pinyin") and r.get("kanji")]

             
                # この下のループ処理を、警告が出るものに差し替えるんだ
                for index, record in enumerate(valid_records):
                    st.markdown("---")
                    
                    # --- 横並びレイアウト ---
                    # カラムを2つ作る。左側にタイトル(比率8)、右側にボタン(比率2)
                    col1, col2 = st.columns([8, 2])
                    
                    with col1:
                        st.write(f"**🎵 問題 {index + 1}**")
                    with col2:
                    # 削除ボタンを押した時に、session_stateに一時的にフラグを立てる
                    # キーを工夫して、どのIDを削除しようとしているかを保持する
                        confirm_key = f"confirm_del_{record['id']}"
                    
                        if st.button(f"🗑️ 削除", key=f"btn_del_{record['id']}"):
                            st.session_state[confirm_key] = True
                    
                    # 削除フラグが立っていたら、確認ボタンを表示
                        if st.session_state.get(confirm_key, False):
                            st.warning("本当に消すか？")
                        # 横並びに「確定」と「キャンセル」を配置
                            c_col1, c_col2 = st.columns(2)
                            with c_col1:
                                if st.button("✅ 確定", key=f"yes_{record['id']}"):
                                    try:
                                        supabase.table("study_data").delete().eq("id", record["id"]).execute()
                                    # 削除したらフラグを消して再読み込み
                                        del st.session_state[confirm_key]
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"失敗: {e}")
                            with c_col2:
                                if st.button("❌ 戻る", key=f"no_{record['id']}"):
                                    st.session_state[confirm_key] = False
                                    st.rerun()
                    # ----------------------
                    
                    # 音声再生と答えの確認
                    st.audio(record["audio_data"], format="audio/mp3")
                    expander_key = f"expander_{record['id']}_{st.session_state[expander_reset_key]}"
                    with st.expander("👁️ 答えを確認する", key=expander_key):
                        st.write(f"📌 ピンイン: {record.get('pinyin')}")
                        st.write(f"🇨🇳 簡体字: {record.get('kanji')}")
                    
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
        import re
        def natural_sort_key(s):
            return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]
        
        existing_folders.sort(key=natural_sort_key)  

        if comp_mode == "データ登録モード":
            # --- 1. フォルダ管理エリア（統一されたデザイン） ---
            with st.expander("🗑️ フォルダを削除する"):
                del_comp_folder = st.selectbox("削除したいフォルダを選択", comp_folders, key="del_comp_folder_sel")
                if st.button("フォルダを削除", key="delete_comp_folder_btn"):
                    if del_comp_folder == "未分類":
                        st.warning("【未分類】は消せないぞ。")
                    else:
                        try:
                            # 中作文(composition)タイプかつ、そのフォルダ名のみを削除
                            supabase.table("study_data")\
                                .delete()\
                                .eq("username", st.session_state.username)\
                                .eq("type", "composition")\
                                .eq("folder_name", del_comp_folder)\
                                .execute()
                            st.success(f"フォルダ【{del_comp_folder}】を中作文データごと消したぞ！")
                            st.rerun()
                        except Exception as e:
                            st.error(f"削除失敗だ: {e}")
            # --- 中作文用のフォルダ名変更エリア ---
            with st.expander("📁 フォルダ名を変更する"):
                # リスニングと区別するために _comp をつける
                old_name = st.selectbox("変更したいフォルダを選択", comp_folders, key="rename_old_comp")
                new_name = st.text_input("新しいフォルダ名を入力", key="rename_new_comp")
                
                if st.button("フォルダ名を変更する", key="rename_btn_comp"):
                    # 「未分類」の変更は防いでおくと安全だ
                    if old_name == "未分類":
                        st.warning("「未分類」は名前変更できないぞ。")
                    elif old_name and new_name.strip():
                        try:
                            # 中作文（composition）タイプのみを対象に更新する
                            supabase.table("study_data").update({"folder_name": new_name.strip()})\
                                .eq("username", st.session_state.username)\
                                .eq("type", "composition")\
                                .eq("folder_name", old_name)\
                                .execute()
                            st.success(f"【{old_name}】を【{new_name.strip()}】に変更したぞ！")
                            st.rerun()
                        except Exception as e:
                            st.error(f"変更失敗だ: {e}")
                    else:
                        st.warning("名前を入力しろ。")
                   
            
            with st.container(border=True):
                st.subheader("📁 フォルダの新規作成")
                new_folder_input = st.text_input("新しいフォルダ名を入力", key="comp_fold_new")
            
                if st.button("フォルダを作成", key="create_comp_fold_btn"):
                    if new_folder_input.strip():
                        try:
                        # データベースへ登録
                            supabase.table("study_data").insert({
                                "username": st.session_state.username,
                                "type": "composition",
                                "folder_name": new_folder_input.strip(),
                                "japanese": "",
                                "kanji": ""
                            }).execute()
                        
                            st.success(f"【{new_folder_input}】を作成したぞ！")
                            st.rerun()
                        except Exception as e:
                            st.error(f"作成失敗だ: {e}")
                    else: 
                    # この else は if new_folder_input.strip(): の直下に置く
                        st.warning("名前を入力しろ。")
            # --- 2. データ登録エリア ---
            st.subheader("📝 中作文データの新規登録")
            folder_choice = st.selectbox("既存のフォルダから選ぶ", comp_folders, key="comp_fold_sel")
            
            st.markdown("---")
            japanese_input = st.text_area("日本語の文章を手入力（問題）", key="comp_jap")
            kanji_input = st.text_area("中国語の文章（簡体字・ピンインなど）を手入力（解答）", key="comp_kanji")

            if st.button("中作文データを保存", key="comp_save_btn"):
                # ここで「新規入力」と「選択」を判定する
                target_folder = new_folder_input.strip() if new_folder_input.strip() else folder_choice
                
                if japanese_input and kanji_input:
                    new_comp = {
                        "username": st.session_state.username,
                        "type": "composition",
                        "japanese": japanese_input,
                        "kanji": kanji_input,
                        "folder_name": target_folder
                    }
                    try:
                        supabase.table("study_data").insert(new_comp).execute()
                        st.success(f"データをフォルダ【{target_folder}】に保存したぞ！")
                        st.rerun()
                    except Exception:
                        st.error("保存失敗だ。")
                else:
                    st.warning("日本語と中国語の両方を入力しろ。")

        else:
            st.subheader("🎯 中作文・ランダムテスト")
            
            # --- 🎯 中作文・ランダムテスト ---
            selected_test_folder = st.selectbox("テストするフォルダを選択しろ", comp_folders, key="comp_test_fold_sel")
            
            comp_cache_key = f"comp_cache_{selected_test_folder}"
            if comp_cache_key not in st.session_state or st.button("🔄 データを最新に更新（反映されない場合は下のシャッフルを押すと上手くいくと思います）", key="comp_refresh_btn"):
                try:
                    # ここでダミーデータ（日本語が空のレコード）を最初から除外する
                    res_comp_rec = supabase.table("study_data")\
                        .select("id, japanese, kanji")\
                        .eq("username", st.session_state.username)\
                        .eq("type", "composition")\
                        .eq("folder_name", selected_test_folder)\
                        .neq("japanese", "")\
                        .execute()
                    
                    st.session_state[comp_cache_key] = res_comp_rec.data if res_comp_rec.data else []
                except Exception:
                    st.session_state[comp_cache_key] = []
            # ... try-except の後の行 ...
            records = st.session_state.get(comp_cache_key, [])
            if not records:
                st.info(f"フォルダ【{selected_test_folder}】にはまだデータがないぞ。")
            # (中略：データの取得と if not records: の部分まで)
            else:
                comp_shuffle_key = f"comp_shuffled_{selected_test_folder}"
            
            # 1. リセット用のキーを管理（ループの前に配置）
                comp_reset_key = f"comp_reset_{selected_test_folder}"
                if comp_reset_key not in st.session_state:
                    st.session_state[comp_reset_key] = 0

                if comp_shuffle_key not in st.session_state or st.button("🔁 このフォルダの問題をシャッフル", key="comp_shuf_btn"):
                    import random
                    shuffled_list = list(records)
                    random.shuffle(shuffled_list)
                    st.session_state[comp_shuffle_key] = shuffled_list
                    st.session_state[comp_reset_key] += 1  # リセット用カウンタを更新
                    st.rerun()

            # 2. ループ処理（ここを差し替えろ）
                for index, record in enumerate(st.session_state[comp_shuffle_key]):
                    rec_id = record["id"]
                    japanese = record["japanese"]
                    kanji = record["kanji"]
                    confirm_key = f"del_confirm_comp_{rec_id}"

                    st.markdown(f"---")
                    col1, col2 = st.columns([6, 1])
                    with col1:
                        st.write(f"**📝 問題 {index + 1}**")
                
                    with col2:
                    # 削除の二段階確認ロジック
                        if st.session_state.get(confirm_key, False):
                            if st.button("✅ 確定", key=f"yes_comp_{rec_id}"):
                                try:
                                    supabase.table("study_data").delete().eq("id", rec_id).execute()
                                    del st.session_state[confirm_key]
                                    st.session_state[comp_cache_key] = [r for r in st.session_state[comp_cache_key] if r["id"] != rec_id]
                                    st.session_state[comp_shuffle_key] = [r for r in st.session_state[comp_shuffle_key] if r["id"] != rec_id]
                                    st.rerun()
                                except Exception:
                                    st.error("削除失敗。")
                            if st.button("❌", key=f"no_comp_{rec_id}"):
                                st.session_state[confirm_key] = False
                                st.rerun()
                        else:
                            if st.button("🗑 削除", key=f"del_comp_{rec_id}"):
                                st.session_state[confirm_key] = True
                                st.rerun()

                    st.info(f"**日本語:** {japanese}")
                
                # 3. シャッフルで閉じるトグル
                    toggle_key = f"toggle_comp_{rec_id}_{st.session_state[comp_reset_key]}"
                    if st.toggle("👀 答えを見る", key=toggle_key):
                        st.success(f"**🇨🇳 中国語:**\n{kanji}")
