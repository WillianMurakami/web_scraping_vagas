import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

def setup_webdriver(headless):
    service = Service('C:/Windows/System32/chromedriver.exe')  # Ajuste o caminho conforme necessário
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument('--headless')  # Executar o navegador de forma invisível
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def fetch_jobs_details_on_main_page(driver, max_vagas):
    job_listings = []
    try:
        last_height = driver.execute_script("return document.body.scrollHeight")

        while len(job_listings) < max_vagas:
            job_elements = driver.find_elements(By.CLASS_NAME, 'sc-4d881605-0')  # Ajuste este seletor conforme necessário

            for job in job_elements:
                if len(job_listings) >= max_vagas:
                    break
                try:
                    title = job.find_element(By.CSS_SELECTOR, "h3.sc-bZkfAO.gYfAYo.sc-4d881605-4.dZRYPZ").text
                    company = job.find_element(By.CSS_SELECTOR, "p.sc-bBXxYQ.eJcDNr.sc-4d881605-5.bpsGtj").text
                    location = job.find_element(By.CSS_SELECTOR, "div[aria-label*='Local']").text
                    pub_date_element = job.find_element(By.CSS_SELECTOR, "p.sc-bBXxYQ.eJcDNr.sc-d9e69618-0.iUzUdL").text
                    pub_date = pub_date_element.replace("Publicada em: ", "").strip()
                    work_type = job.find_element(By.CSS_SELECTOR, "div[aria-label*='Modelo de trabalho']").find_element(By.TAG_NAME, 'span').text
                    hire_type = job.find_element(By.CSS_SELECTOR, "div[aria-label*='Essa vaga é do tipo']").find_element(By.TAG_NAME, 'span').text
                    job_link = job.find_element(By.CSS_SELECTOR, "a.sc-4d881605-1.IKqnq").get_attribute('href')

                    # Se a modalide de trabalho indicar remoto, definir localização como 'Remota'
                    if 'remoto' in work_type.lower():
                        location = "Remota"

                    job_listings.append({
                        "Título": title,
                        "Empresa": company,
                        "Localização": location,
                        "Data de Publicação": pub_date,
                        "Modalidade de Trabalho": work_type,
                        "Modalidade de Contratação": hire_type,
                        "Link para Vaga": job_link,
                        "Responsabilidades": "Não informado",
                        "Requisitos e Qualificações": "Não informado",
                    })
                except Exception as e:
                    print(f"Erro ao processar a vaga na página principal: {e}")

            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)

            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    except Exception as e:
        print(f"Erro ao capturar detalhes das vagas na página principal: {e}")

    return job_listings

def fetch_detailed_job_info(link, headless):
    driver = setup_webdriver(headless)
    driver.get(link)
    time.sleep(3)

    responsibilities, qualifications = "Não informado", "Não informado"

    try:
        responsibilities = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), 'Responsabilidades')]/following-sibling::div"))
        ).text
    except Exception as e:
        print(f"Erro ao obter responsabilidades: {e}")

    try:
        qualifications = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), 'Requisitos')]/following-sibling::div"))
        ).text
    except Exception as e:
        print(f"Erro ao obter qualificações: {e}")

    driver.quit()
    return responsibilities, qualifications

def fetch_jobs_selenium(term, max_vagas, headless):
    driver = setup_webdriver(headless)
    all_jobs = []

    try:
        url = f"https://portal.gupy.io/job-search/term={term.replace(' ', '%20')}"
        driver.get(url)
        time.sleep(3)

        all_jobs.extend(fetch_jobs_details_on_main_page(driver, max_vagas))

    finally:
        driver.quit()

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(fetch_detailed_job_info, job["Link para Vaga"], headless) for job in all_jobs]
        for i, future in enumerate(futures):
            responsibilities, qualifications = future.result()
            all_jobs[i]["Responsabilidades"] = responsibilities
            all_jobs[i]["Requisitos e Qualificações"] = qualifications

    df = pd.DataFrame(all_jobs)

    # Dividir localização em Cidade e Estado
    if 'Localização' in df.columns:
        df[['Cidade', 'Estado']] = df['Localização'].apply(lambda x: x.split('-') if '-' in x else (x, '')).tolist()
        df.drop('Localização', axis=1, inplace=True)

    return df

def convert_df_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Vagas')
    processed_data = output.getvalue()
    return processed_data

# Interface do Streamlit
st.set_page_config(page_title="Dashboard de Vagas", layout="wide")

st.sidebar.title("Informações")
st.sidebar.markdown("Projeto desenvolvido por [Willian Murakami](https://www.linkedin.com/in/willian-murakami/)")

st.title("📊 Dashboard de Vagas - Gupy")
st.markdown(
    "Bem-vindo ao sistema de pesquisa de vagas! Aqui você pode buscar oportunidades de emprego com base em seus critérios "
    "e obter detalhes completos sobre cada posição disponível. Lembrando que quanto mais vagas forem solicitadas mais tempo o sistema precisará para fazer a coelta dos dados."
)

col1, col2 = st.columns([3, 1])
with col1:
    term = st.text_input("Digite o termo de busca para as vagas:")
with col2:
    quantidade_vagas = st.number_input("Quantidade de vagas:", min_value=1, step=1, value=10)

show_scraping_process = st.toggle("Mostrar processo de Scraping")

if st.button("Buscar Vagas"):
    with st.spinner("Buscando vagas..."):
        df_vagas = fetch_jobs_selenium(term, quantidade_vagas, not show_scraping_process)
        st.session_state.df_vagas = df_vagas

if 'df_vagas' in st.session_state and not st.session_state.df_vagas.empty:
    st.success(f"Foram encontradas {len(st.session_state.df_vagas)} vagas!")
    st.dataframe(st.session_state.df_vagas.style.set_properties(**{'white-space': 'nowrap', 'overflow-x': 'auto'}))

    xlsx_data = convert_df_to_excel(st.session_state.df_vagas)
    st.download_button(
        label="Baixar resultados como XLSX",
        data=xlsx_data,
        file_name='vagas.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )