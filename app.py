import os
import google.generativeai as genai
import streamlit as st
from pathlib import Path

# Konfigurasi API Gemini
def setup_gemini():
    genai.configure(api_key=os.environ.get('GOOGLE_API_KEY'))
    model = genai.GenerativeModel('gemini-1.5-flash')
    return model

# Daftar contoh prompt
SAMPLE_PROMPTS = [
    "(Prompt#1) Anda adalah seorang ahli ontologi dalam konteks data statistik. Pelajari file GSBPM dan GSIM berikut:",
    "(Prompt#2) Sebutkan beberapa class yang ada di GSBPM dan GSIM!",
    """(Prompt#3) Pelajari bahwa knowledge di atas (GSBPM, GSIM, SDPO) dapat digunakan untuk menentukan class dalam ontology, seperti contoh berikut:
    1. Dari tabel master_kegiatan + kolom judul_kegiatan, maka class yang digunakan adalah StatisticalProgram
    2. Dari tabel master_kegiatan + kolom judul_kegiatan + tahun_kegiatan, maka class yang digunakan adalah StatisticalProgramCycle

    Dan pelajari bahwa knowledge di atas juga dapat digunakan untuk menentukan properties, seperti contoh berikut:
    1. Dari tabel master_kegiatan + kolom tujuan_kegiatan, maka properties yang digunakan adalah hasObjective-SP
    2. Dari tabel master_kegiatan + kolom tujuan_kegiatan, maka properties yang digunakan adalah hasStatus-SP
    """,
    "(Prompt#4) Berdasarkan konteks dan contoh yang sudah dipelajari sebelumnya, tebak Class, Data Properties dan Object properties untuk setiap kolom dari semua tabel di database MS SQL terlampir:",
    """(Prompt#5) Buatkan ontologi lokal lengkap dalam format Turtle (.ttl) dari skema seluruh tabel yang saya miliki di atas, berdasarkan ontologi global dan contoh ontologi lokal sirusa yang sudah dipelajari.
        Pastikan hasilnya adalah RDF/Turtle yang valid dengan:
        1. Prefix dan namespace yang benar
        2. Class untuk setiap tabel
        3. Property untuk setiap kolom
        4. Relasi antar tabel jika terlihat dari nama kolom
        5. Gunakan standard ontology seperti rdfs:label, rdf:type dll
        6. Gunakan Base IRI dengan format: "(website_resmi_sumber_data)/metadata/(nama_database)"
            Contoh:
            Jika nama database adalah "sirusa", maka IRI: https://www.bps.go.id/metadata/sirusa/
            Jika nama database adalah "survey", maka IRI: https://www.bps.go.id/metadata/survey/
            Jika nama database adalah "data_extraction", maka IRI: https://www.bps.go.id/metadata/data_extraction
        7. Gunakan actual data dari seluruh tabel yang saya miliki tersebut untuk bagian Individuals, bukan dummy/examples data.
    """
]

# Fungsi untuk membaca file teks
def read_text_file(file):
    try:
        content = file.read().decode('utf-8')
        return content
    except Exception as e:
        st.error(f"Error membaca file {file.name}: {str(e)}")
        return None

# Fungsi untuk mendapatkan respons dari Gemini
def get_gemini_response(model, prompt, files_content):
    try:
        if files_content:
            full_prompt = f"{prompt}\n\nKonten dari file-file yang diupload:\n\n"
            for filename, content in files_content.items():
                full_prompt += f"=== {filename} ===\n{content}\n\n"
        else:
            full_prompt = prompt
            
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

# Aplikasi Streamlit
def main():
    st.title("💬 Automatic Local Ontology Builder (use case Statistical Metadatabase)")
    
    # Setup session state
    if 'model' not in st.session_state:
        st.session_state.model = setup_gemini()
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'files_content' not in st.session_state:
        st.session_state.files_content = {}
    if 'active_files' not in st.session_state:
        st.session_state.active_files = set()
    
    # Sidebar untuk upload file dan pilihan prompt
    with st.sidebar:
        st.header("Pengaturan")
        
        # Multiple file uploader
        uploaded_files = st.file_uploader(
            "Upload file teks (bisa multiple)", 
            type=['txt'], 
            accept_multiple_files=True
        )
        
        # Update active files berdasarkan file yang diupload
        current_files = {file.name for file in uploaded_files} if uploaded_files else set()
        st.session_state.active_files = current_files
        
        # Button untuk menghapus semua file
        if st.button("Hapus Semua File"):
            st.session_state.files_content = {}
            st.session_state.active_files = set()
            st.success("Semua file telah dihapus!")
        
        # Proses file yang diupload
        if uploaded_files:
            st.session_state.files_content = {}
            for uploaded_file in uploaded_files:
                content = read_text_file(uploaded_file)
                if content:
                    st.session_state.files_content[uploaded_file.name] = content
            
            if st.session_state.files_content:
                st.success(f"{len(st.session_state.files_content)} file berhasil diupload!")
                
                # Expander untuk setiap file
                for filename, content in st.session_state.files_content.items():
                    with st.expander(f"📄 {filename}"):
                        st.text_area("Isi file:", value=content, height=150, disabled=True)
        
        # Dropdown untuk contoh prompt
        st.header("Contoh Prompt")
        selected_prompt = st.selectbox(
            "Pilih prompt:",
            [""] + SAMPLE_PROMPTS,
            key="prompt_selector"
        )
        
        # Tombol untuk mengirim prompt yang dipilih
        if selected_prompt and st.button("Gunakan Prompt Ini"):
            # Simpan pesan dengan prompt yang dipilih
            with st.chat_message("user"):
                st.write(selected_prompt)
                if st.session_state.files_content:
                    st.caption(f"File yang digunakan: {', '.join(st.session_state.active_files)}")
            
            user_message = {
                "role": "user", 
                "content": selected_prompt,
                "files_used": list(st.session_state.active_files)
            }
            st.session_state.messages.append(user_message)
            
            # Dapatkan respons dari Gemini
            with st.chat_message("assistant"):
                response = get_gemini_response(
                    st.session_state.model, 
                    selected_prompt, 
                    st.session_state.files_content
                )
                st.write(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()

    # Area chat
    chat_container = st.container()
    with chat_container:
        # Tampilkan riwayat chat dengan pengecekan file yang masih aktif
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
                
                # Tampilkan info file yang digunakan, hanya jika ada file yang aktif
                if message["role"] == "user" and "files_used" in message:
                    # Filter hanya file yang masih aktif
                    active_files_used = [
                        file for file in message["files_used"] 
                        if file in st.session_state.active_files
                    ]
                    if active_files_used:
                        st.caption(f"File yang digunakan: {', '.join(active_files_used)}")

    # Input chat normal
    prompt_input = st.chat_input("Ketik pesan atau pilih prompt dari sidebar...")
    
    if prompt_input:
        # Tampilkan pesan user
        with st.chat_message("user"):
            st.write(prompt_input)
            if st.session_state.active_files:
                st.caption(f"File yang digunakan: {', '.join(st.session_state.active_files)}")
        
        # Simpan pesan dengan info file yang digunakan
        user_message = {
            "role": "user", 
            "content": prompt_input,
            "files_used": list(st.session_state.active_files)
        }
        st.session_state.messages.append(user_message)
        
        # Dapatkan respons dari Gemini
        with st.chat_message("assistant"):
            response = get_gemini_response(
                st.session_state.model, 
                prompt_input, 
                st.session_state.files_content
            )
            st.write(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main()
