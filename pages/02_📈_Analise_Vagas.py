import streamlit as st
import pandas as pd
import spacy
from collections import Counter
import plotly.express as px
from datetime import datetime

# Carregar o modelo de idioma português do spaCy
nlp = spacy.load("pt_core_news_sm")

# Stopwords adicionais específicas para este contexto
additional_stopwords = {
    "via", "forte", "fins", "setor", "cargo", "assim", "uso", "área", "caso", "utilizando", "semana", "gosto", "precisamos", "conhecimento", "áreas", 
    "público", "criar", "capacidade", "ferramentas", "ferramenta", "práticas", "prática", "concluído", "formação",  
    "atividade", "comprovada", "sp", "cursando", "melhoria", "conceitos", "aumentar", "otimizar", "região", "pirataria", 
    "precisamos", "riscos", "diferencial", "utilizados", "experiência", "será", "deve", "deverá"
}

# Função para processar texto e contar termos
def normalize_terms(text):
    doc = nlp(text.lower())
    tokens = [
        token.text for token in doc 
        if token.is_alpha and not token.is_stop and token.text not in additional_stopwords
    ]
    return Counter(tokens)

def extract_skills_and_tools(df):
    hard_skills = Counter()
    soft_skills = Counter()
    tools = Counter()

    requisitos_qualificacoes = " ".join(df['Requisitos e Qualificações'].dropna())
    responsabilidades = " ".join(df['Responsabilidades'].dropna())
    combined_text = requisitos_qualificacoes + " " + responsabilidades

    hard_skills.update(normalize_terms(requisitos_qualificacoes))
    soft_skills.update(normalize_terms(requisitos_qualificacoes))
    tools.update(normalize_terms(combined_text))

    return hard_skills, soft_skills, tools

# Verificar se os dados do scraping estão presentes
if 'df_vagas' not in st.session_state or st.session_state.df_vagas.empty:
    st.warning("Nenhum dado de vaga encontrado. Por favor, faça a busca de vagas antes de acessar a análise.")
else:
    df_vagas = st.session_state.df_vagas

    df_vagas['Data de Publicação'] = pd.to_datetime(df_vagas['Data de Publicação'], errors='coerce').dt.date
    if 'Data de Candidatura' in df_vagas.columns:
        df_vagas['Data de Candidatura'] = pd.to_datetime(df_vagas['Data de Candidatura'], errors='coerce').dt.date

    st.title("Análise de Vagas 📈")
    st.markdown("""Aqui temos as principais informações das vagas. 
Nesse painel você encontrará informações para facilitar sua análise e compreensão sobre a área pesquisada!""")

    # Linha 1: Cartão, Total de Dias Observados e Controle de Tempo
    col1, col2, col3 = st.columns([0.3, 0.3, 0.4])

    with col1:
        total_vagas = len(df_vagas)
        st.metric(label="Total de Vagas", value=total_vagas)

    data_min = min(df_vagas['Data de Publicação'])
    data_max = max(df_vagas['Data de Publicação'])
    total_dias = (data_max - data_min).days
    with col2:
        st.metric(label="Total de Dias Observados", value=total_dias)

    with col3:
        selected_date = st.slider("Controle de Tempo", min_value=data_min, max_value=data_max, value=(data_min, data_max))

    df_filtered = df_vagas[(df_vagas['Data de Publicação'] >= selected_date[0]) & (df_vagas['Data de Publicação'] <= selected_date[1])]

    # Gráfico de Linhas - Vagas por Data
    if not df_filtered['Data de Publicação'].isnull().all():
        publicacao_counts = df_filtered['Data de Publicação'].value_counts().sort_index()
        candidatura_counts = df_filtered['Data de Candidatura'].value_counts().sort_index() if 'Data de Candidatura' in df_filtered.columns else pd.Series()

        fig_publicacao = px.line(x=publicacao_counts.index, y=publicacao_counts.values, labels={'x': 'Data', 'y': 'Número de Vagas'}, title='Vagas por Data de Publicação')
        fig_publicacao.add_scatter(x=candidatura_counts.index, y=candidatura_counts.values, mode='lines+markers', name='Candidaturas')
        st.plotly_chart(fig_publicacao)

    # Vagas por Empresa e Gráfico Sunburst
    col4, col5 = st.columns([0.4, 0.6])

    with col4:
        empresa_counts = df_filtered['Empresa'].value_counts()
        empresa_fig = px.bar(empresa_counts, y=empresa_counts.index, x=empresa_counts.values, orientation='h', 
                             title='Vagas por Empresa')
        empresa_fig.update_layout(yaxis_title='Empresas', xaxis_title='Número de Vagas', 
                                  plot_bgcolor='rgba(0,0,0,0)', yaxis=dict(showgrid=True), xaxis=dict(showgrid=True))
        st.plotly_chart(empresa_fig)

    with col5:
        sunburst_data = df_filtered.groupby(['Estado', 'Cidade']).size().reset_index(name='Número de Vagas')

        sunburst_fig = px.sunburst(
            sunburst_data,
            path=['Estado', 'Cidade'],
            values='Número de Vagas',
            title="Distribuição de Vagas por Estado e Cidade"
        )
        st.plotly_chart(sunburst_fig)

    # Modalidade do Trabalho e Treemap
    col6, col7 = st.columns([0.5, 0.5])

    with col6:
        if 'Modalidade de Contratação' in df_filtered.columns:
            contrato_counts = df_filtered['Modalidade de Contratação'].value_counts().reset_index()
            contrato_counts.columns = ['Modalidade', 'Contagem']
            contrato_counts['Percentual'] = 100 * contrato_counts['Contagem'] / contrato_counts['Contagem'].sum()

            work_type_fig = px.bar(
                contrato_counts, x='Modalidade', y='Contagem', text='Percentual',
                labels={'y': 'Número de Vagas'}, title='Modalidade de Contratação'
            )
            work_type_fig.update_traces(texttemplate='%{text:.2f}%', textposition='inside')
            st.plotly_chart(work_type_fig)

    with col7:
        if 'Modalidade de Trabalho' in df_filtered.columns:
            treemap_data = df_filtered['Modalidade de Trabalho'].value_counts().reset_index()
            treemap_data.columns = ['Modalidade', 'Contagem']
            treemap_data['Percentual'] = 100 * treemap_data['Contagem'] / treemap_data['Contagem'].sum()

            treemap_fig = px.treemap(
                treemap_data, path=['Modalidade'], values='Contagem', title="Modalidade de Trabalho",
                hover_data={'Contagem': True, 'Percentual': True}
            )
            treemap_fig.update_traces(texttemplate='<b>%{label}</b><br>%{value} vagas<br>%{percentParent:.2f}% do total')
            st.plotly_chart(treemap_fig)

    # Análise de Texto: Extração e Visualização de Habilidades e Ferramentas
    st.header("Análise de Habilidades e Ferramentas")

    hard_skills, soft_skills, tools = extract_skills_and_tools(df_filtered)

    st.subheader("Hard Skills e Certificações")
    fig_hard_skills = px.bar(x=list(hard_skills.keys()), y=list(hard_skills.values()), title="Hard Skills Frequentes")
    st.plotly_chart(fig_hard_skills)

    st.subheader("Soft Skills")
    fig_soft_skills = px.bar(x=list(soft_skills.keys()), y=list(soft_skills.values()), title="Soft Skills Frequentes")
    st.plotly_chart(fig_soft_skills)

    st.subheader("Ferramentas Utilizadas")
    tools_data = pd.DataFrame(tools.items(), columns=['Ferramenta', 'Frequência'])
    fig_tools = px.treemap(tools_data, path=['Ferramenta'], values='Frequência', title="Distribuição de Ferramentas Utilizadas")
    fig_tools.update_traces(tiling=dict(pad=1))
    st.plotly_chart(fig_tools)