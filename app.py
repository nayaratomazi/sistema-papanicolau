import streamlit as st
import pdfplumber
import pandas as pd

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(
    page_title="Gestão de Citologia",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. LOGO E CABEÇALHO
col_logo, col_titulo = st.columns([1, 5])

with col_logo:
    st.image(
        "https://paineis-ext.mpdft.mp.br/extensions/mapasaude/logo-saude-da-familia.png",
        width=100
    )

with col_titulo:
    st.title("Gestão de Laudos de Citopatologia")
    st.markdown("##### *Painel de Monitoramento da Estratégia Saúde da Família*")

st.markdown("---")

# 3. ACESSO
senha_correta = "esf2026"
acesso = st.sidebar.text_input("🔐 Senha da Coordenação", type="password")

if acesso == senha_correta:

    arquivos = st.file_uploader("📂 Carregar PDFs dos Laudos", type=["pdf"], accept_multiple_files=True)

    if arquivos:
        dados = []

        for arquivo in arquivos:
            with pdfplumber.open(arquivo) as pdf:
                for pagina in pdf.pages:
                    texto = pagina.extract_text()

                    if not texto:
                        continue

                    if "Idade:" in texto:

                        idade = texto.split("Idade:")[1].split()[0]

                        coleta = (
                            texto.split("Data da coleta:")[1].split()[0]
                            if "Data da coleta:" in texto
                            else "N/A"
                        )

                        zt = (
                            texto.split("TRANSFORMAÇÃO:")[1].split()[0]
                            if "TRANSFORMAÇÃO:" in texto
                            else "N/A"
                        )

                        resultado = (
                            texto.split("CONCLUSÃO")[1][:200]
                            if "CONCLUSÃO" in texto
                            else "N/A"
                        )

                        nascimento = (
                            texto.upper()
                            .split("DATA DO NASCIMENTO")[1]
                            .replace(":", "")
                            .split()[0]
                            if "DATA DO NASCIMENTO" in texto.upper()
                            else "N/A"
                        )

                        unidade = (
                            texto.split("Nome:")[1].split("\n")[0]
                            if "Nome:" in texto
                            else "N/A"
                        )

                        amostra = (
                            texto.split("AMOSTRA")[1].split("\n")[0][:50]
                            if "AMOSTRA" in texto
                            else "N/A"
                        )

                        nome_cru = (
                            texto.split("Nome:")[2].split("\n")[0]
                            if texto.count("Nome:") > 1
                            else ""
                        )

                        nome_limpo = (
                            nome_cru.split("Idade")[0]
                            .split("Data")[0]
                            .split("Nasc")[0]
                        )

                        iniciais = (
                            "".join([p[0].upper() for p in nome_limpo.split() if p and p[0].isalpha()])
                            if nome_limpo
                            else "N/A"
                        )

                        endereco = (
                            texto.split("Endereço:")[1].split("\n")[0][:40]
                            if "Endereço:" in texto
                            else "N/A"
                        )

                        epitelios = (
                            texto.upper()
                            .split("EPITÉLIOS REPRESENTADOS NA AMOSTRA")[1]
                            .split("\n")[0]
                            .replace(":", "")
                            .strip()
                            if "EPITÉLIOS REPRESENTADOS NA AMOSTRA" in texto.upper()
                            else "N/A"
                        )

                        microbiologia = (
                            texto.upper()
                            .split("MICROBIOLOGIA")[1]
                            .split("\n")[0]
                            .replace(":", "")
                            .strip()
                            if "MICROBIOLOGIA" in texto.upper()
                            else "N/A"
                        )

                        alteracoes = (
                            texto.upper()
                            .split("ALTERAÇÕES CELULARES BENIGNAS")[1]
                            .split("\n")[0]
                            .replace(":", "")
                            .strip()
                            if "ALTERAÇÕES CELULARES BENIGNAS" in texto.upper()
                            else "N/A"
                        )

                        dados.append({
                            "Unidade": unidade,
                            "Iniciais": iniciais,
                            "Nascimento": nascimento,
                            "Idade": idade,
                            "Coleta": coleta,
                            "Endereço": endereco,
                            "Amostra": amostra,
                            "Epitélios": epitelios,
                            "ZT": zt,
                            "Microbiologia": microbiologia,
                            "Alterações": alteracoes,
                            "Resultado": resultado,
                        })

        tabela = pd.DataFrame(dados)

        termos_alerta = ["ASC-US", "ASC-H", "BAIXO GRAU", "ALTO GRAU", "REPETIR", "LESÃO", "ATIPIAS", "CARCINOMA"]

        tabela["Alterado"] = tabela["Resultado"].str.upper().apply(
            lambda x: any(t in str(x) for t in termos_alerta)
        )

        def destacar_alterados(linha):
            cor = "background-color: #ffffb3; color: black" if linha["Alterado"] else ""
            return [cor for _ in linha]

        tabela["Coleta_Data"] = pd.to_datetime(tabela["Coleta"], errors="coerce")
        tabela["Mês"] = tabela["Coleta_Data"].dt.strftime("%m/%Y")

        # FILTROS
        st.sidebar.markdown("## 🔎 Filtros")

        meses_disponiveis = sorted(tabela["Mês"].dropna().unique())
        mes_selecionado = st.sidebar.selectbox("📅 Filtrar por Mês", ["Todos"] + list(meses_disponiveis))

        filtro_resultado = st.sidebar.selectbox(
            "🧪 Filtrar por Resultado",
            ["Todos", "Somente Alterados", "Somente Normais"]
        )

        tabela_filtrada = tabela.copy()

        if mes_selecionado != "Todos":
            tabela_filtrada = tabela_filtrada[tabela_filtrada["Mês"] == mes_selecionado]

        if filtro_resultado == "Somente Alterados":
            tabela_filtrada = tabela_filtrada[tabela_filtrada["Alterado"] == True]
        elif filtro_resultado == "Somente Normais":
            tabela_filtrada = tabela_filtrada[tabela_filtrada["Alterado"] == False]

        total_alterados = tabela_filtrada["Alterado"].sum()

        if total_alterados > 0:
            st.error(f"🚨 ATENÇÃO: {total_alterados} caso(s) alterado(s) identificado(s)!")
        else:
            st.success("✅ Nenhum caso alterado nos filtros aplicados.")

        tabela_filtrada["Idade_Num"] = pd.to_numeric(tabela_filtrada["Idade"], errors="coerce")

        na_faixa = len(tabela_filtrada[(tabela_filtrada["Idade_Num"] >= 25) & (tabela_filtrada["Idade_Num"] <= 64)])
        fora_faixa = len(tabela_filtrada) - na_faixa

        satisfatoria = len(
            tabela_filtrada[tabela_filtrada["Amostra"].str.contains("SATISFAT", case=False, na=False)]
        )

        dois_epitelios = len(
            tabela_filtrada[
                tabela_filtrada["Epitélios"].str.contains("ESCAMOSO", case=False, na=False)
                & tabela_filtrada["Epitélios"].str.contains("GLANDULAR", case=False, na=False)
            ]
        )

        # ABAS
        aba1, aba2 = st.tabs(["📊 Indicadores de Qualidade", "📋 Monitoramento de Pacientes"])

        with aba1:
            st.subheader("Parâmetros do Ministério da Saúde")
            col1, col2, col3 = st.columns(3)
            col1.metric("Na Faixa Etária (25-64)", na_faixa)
            col2.metric("Fora da Faixa", fora_faixa)
            col3.metric("Amostras Satisfatórias", satisfatoria)

            st.markdown("---")
            st.subheader("📊 Visualização Personalizada")

            col_op1, col_op2 = st.columns(2)

            with col_op1:
                variavel = st.selectbox(
                    "Escolha o indicador:",
                    ["Microbiologia", "Representação de Epitélios"]
                )

            with col_op2:
                tipo_grafico = st.selectbox(
                    "Tipo de gráfico:",
                    ["Barra", "Linha", "Pizza"]
                )

            if variavel == "Microbiologia":
                dados_grafico = tabela_filtrada["Microbiologia"].value_counts()
            else:
                dados_grafico = pd.Series({
                    "Ambos Presentes": dois_epitelios,
                    "Faltando": len(tabela_filtrada) - dois_epitelios
                })

            if tipo_grafico == "Barra":
                st.bar_chart(dados_grafico)
            elif tipo_grafico == "Linha":
                st.line_chart(dados_grafico)
            elif tipo_grafico == "Pizza":
                fig, ax = plt.subplots()
                ax.pie(dados_grafico, labels=dados_grafico.index, autopct="%1.1f%%")
                ax.set_title(variavel)
                st.pyplot(fig)

        with aba2:
            st.write("### Tabela de Controle (Casos alterados em destaque)")
            st.dataframe(
                tabela_filtrada.style.apply(destacar_alterados, axis=1),
                use_container_width=True
            )

            st.markdown("---")
            csv = tabela_filtrada.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                "📥 Baixar Planilha Conforme Filtro (.csv)",
                csv,
                "relatorio_filtrado.csv",
                "text/csv"
            )