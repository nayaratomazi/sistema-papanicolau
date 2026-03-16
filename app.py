import streamlit as st
import pdfplumber
import pandas as pd
import matplotlib.pyplot as plt

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(
    page_title="Gestão de Citologia",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILIZAÇÃO CSS (Centralizar senha e limpar UI) ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp { background-color: #f8f9fa; }
    /* Estilo para centralizar o container da senha */
    .auth-container {
        display: flex;
        justify-content: center;
        align-items: center;
        flex-direction: column;
        padding: 50px;
        border-radius: 15px;
        background: white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# 2. LOGO E CABEÇALHO (Sempre visível)
col_logo, col_titulo = st.columns([1, 5])
with col_logo:
    st.image("https://paineis-ext.mpdft.mp.br/extensions/mapasaude/logo-saude-da-familia.png", width=100)
with col_titulo:
    st.title("Gestão de Laudos de Citopatologia")
    st.markdown("##### *Painel de Monitoramento da Estratégia Saúde da Família*")

st.markdown("---")

# 3. LÓGICA DE ACESSO CENTRALIZADA
senha_correta = "esf2026"

# Se não houver acesso na sessão, mostra o campo no meio
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    _, col_central, _ = st.columns([1, 2, 1])
    with col_central:
        st.markdown('<div class="auth-container">', unsafe_allow_html=True)
        st.subheader("🔐 Acesso Restrito")
        senha_input = st.text_input("Digite a senha da coordenação para liberar o painel:", type="password")
        if st.button("Entrar"):
            if senha_input == senha_correta:
                st.session_state['autenticado'] = True
                st.rerun()
            else:
                st.error("Senha incorreta. Tente novamente.")
        st.markdown('</div>', unsafe_allow_html=True)
else:
    # --- CONTEÚDO DO SISTEMA (SÓ APARECE APÓS A SENHA) ---
    st.sidebar.success("✅ Acesso Autorizado")
    if st.sidebar.button("Sair/Bloquear"):
        st.session_state['autenticado'] = False
        st.rerun()

    arquivos = st.file_uploader("📂 Carregar PDFs dos Laudos", type=["pdf"], accept_multiple_files=True)

    if arquivos:
        dados = []
        with st.spinner('Processando laudos...'):
            for arquivo in arquivos:
                with pdfplumber.open(arquivo) as pdf:
                    for pagina in pdf.pages:
                        texto = pagina.extract_text()
                        if not texto or "Idade:" not in texto:
                            continue

                        # --- EXTRAÇÃO (Sua lógica do VS Code) ---
                        idade = texto.split("Idade:")[1].split()[0]
                        coleta = texto.split("Data da coleta:")[1].split()[0] if "Data da coleta:" in texto else "N/A"
                        unidade = texto.split("Nome:")[1].split("\n")[0] if "Nome:" in texto else "N/A"
                        resultado = texto.split("CONCLUSÃO")[1][:200].strip() if "CONCLUSÃO" in texto else "N/A"
                        
                        # Nascimento e Iniciais
                        nasc = texto.upper().split("DATA DO NASCIMENTO")[1].replace(":", "").split()[0] if "DATA DO NASCIMENTO" in texto.upper() else "N/A"
                        nome_cru = texto.split("Nome:")[2].split("\n")[0] if texto.count("Nome:") > 1 else ""
                        iniciais = "".join([p[0].upper() for p in nome_cru.split() if p and p[0].isalpha() and p.lower() not in ['idade', 'data']])

                        # Microbiologia e Epitélios
                        microbio = texto.upper().split("MICROBIOLOGIA")[1].split("\n")[0].replace(":", "").strip() if "MICROBIOLOGIA" in texto.upper() else "N/A"
                        epitelio = texto.upper().split("EPITÉLIOS REPRESENTADOS NA AMOSTRA")[1].split("\n")[0].replace(":", "").strip() if "EPITÉLIOS REPRESENTADOS NA AMOSTRA" in texto.upper() else "N/A"
                        amostra = texto.split("AMOSTRA")[1].split("\n")[0][:50] if "AMOSTRA" in texto else "N/A"

                        dados.append({
                            "Unidade": unidade, "Iniciais": iniciais, "Nascimento": nasc,
                            "Idade": idade, "Coleta": coleta, "Amostra": amostra,
                            "Epitélios": epitelio, "Microbiologia": microbio, "Resultado": resultado
                        })

        if dados:
            df = pd.DataFrame(dados)
            df["Idade_Num"] = pd.to_numeric(df["Idade"], errors="coerce")
            
            # Filtro de Alterados
            termos = ["ASC-US", "ASC-H", "BAIXO GRAU", "ALTO GRAU", "REPETIR", "LESÃO", "ATIPIAS", "CARCINOMA", "NIC"]
            df["Alterado"] = df["Resultado"].str.upper().apply(lambda x: any(t in str(x) for t in termos))

            # --- FILTROS LATERAIS ---
            st.sidebar.header("🔎 Filtros")
            f_status = st.sidebar.selectbox("Filtrar Resultado", ["Todos", "Somente Alterados", "Somente Normais"])
            
            df_f = df.copy()
            if f_status == "Somente Alterados": df_f = df_f[df_f["Alterado"]]
            elif f_status == "Somente Normais": df_f = df_f[~df_f["Alterado"]]

            # --- EXIBIÇÃO ---
            aba1, aba2 = st.tabs(["📊 Indicadores", "📋 Tabela de Monitoramento"])

            with aba1:
                col_m1, col_m2, col_m3 = st.columns(3)
                col_m1.metric("Total de Laudos", len(df_f))
                col_m2.metric("Na Faixa (25-64)", len(df_f[(df_f["Idade_Num"]>=25) & (df_f["Idade_Num"]<=64)]))
                col_m3.metric("Alterações", int(df_f["Alterado"].sum()))
                
                st.markdown("---")
                c_g1, c_g2 = st.columns(2)
                with c_g1:
                    st.write("### Microbiologia")
                    fig, ax = plt.subplots()
                    df_f["Microbiologia"].value_counts().plot.pie(autopct='%1.1f%%', ax=ax)
                    st.pyplot(fig)
                with c_g2:
                    st.write("### Epitélios")
                    st.bar_chart(df_f["Epitélios"].value_counts())

            with aba2:
                st.dataframe(df_f.style.apply(lambda x: ['background-color: #ffcccc' if x.Alterado else '' for _ in x], axis=1))
                csv = df_f.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 Baixar Dados (CSV)", csv, "relatorio.csv", "text/csv")
        else:
            st.info("Aguardando upload de arquivos...")
