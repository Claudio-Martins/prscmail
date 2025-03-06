import shutil
import smtplib
import schedule
import logging
import time
import json
import os
import re
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from logging.handlers import RotatingFileHandler
import hashlib

def calculate_file_hash(filename):
    """Calcula o hash MD5 do conteúdo do arquivo."""
    hash_md5 = hashlib.md5()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

# Configuração do logger
# Nome do arquivo de log
log_file = 'email_sender.log'
# Tamanho máximo do log em bytes (5 MB)
max_log_size = 5 * 1024 * 1024
# Número máximo de arquivos de log a serem mantidos
backup_count = 5

handler = RotatingFileHandler(log_file, maxBytes=max_log_size, backupCount=backup_count)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(handler)


# Função para carregar configurações do arquivo JSON
def load_config(filename):
    try:
        with open(filename, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        logging.error(f"Erro: Ficheiro de configuração '{filename}' não encontrado.")
        return {}
    except json.JSONDecodeError:
        logging.error(f"Erro: Ficheiro de configuração '{filename}' nao é um JSON válido.")
        return {}


# Função para validar a estrutura básica de um endereço
def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


# Função para carregar contactos a partir de tt
def load_emails_from_file(filename):
    try:
        with open(filename, 'r') as file:
            emails = [line.strip() for line in file if line.strip()]
            valid_emails = list(set(email for email in emails if is_valid_email(email)))
            if len(valid_emails) < len(emails):
                logging.warning("Alguns endereços de email inválidos foram encontrados e removidos.")
            return valid_emails
    except FileNotFoundError:
        logging.error(f"Erro: Ficheiro de contactos '{filename}' não encontrado.")
        return []


# Função para enviar e-mail
def send_email(email_config, config, filename):
    from_email = config['smtp']['email']
    password = config['smtp']['password']
    smtp_server = config['smtp']['server']
    smtp_port = config['smtp']['port']

    # Verifica se to_email é uma lista ou um arquivo
    if isinstance(email_config['to_email'], list):
        to_email = email_config['to_email']
    else:
        to_email = load_emails_from_file(os.path.join(contacts_folder, email_config['to_email']))

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = from_email
    msg['Bcc'] = ', '.join(to_email)
    msg['Subject'] = email_config['subject']

    msg.attach(MIMEText(email_config['body'], 'plain'))

    # Retry mechanism
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(from_email, password)
                server.send_message(msg)
                logging.info(f"E-mail enviado para {to_email}")
                break  # Sair do loop se email for bem enviado
        except smtplib.SMTPException as e:
            logging.error(f"Erro ao enviar e-mail para {to_email}: {e}")
            if attempt < max_retries - 1:
                logging.info(f"Tentar novamente em 5 segundos... (Tentativa {attempt + 2}/{max_retries})")
                time.sleep(5)  # Esperar antes de enviar
            else:
                logging.error(f"Falha ao enviar e-mail para {to_email} após {max_retries} tentativas.")
                return  # Sair depois de tentativas esgotadas

    # Atualiza a data de envio se a recorrência estiver definida
    if email_config["recurrence_day"]:
        logging.info(f'INFO: encontrada recurrência para dia {email_config["recurrence_day"]} do próximo mês')
        update_recurrence_date(email_config, filename)
    else:
        logging.info('INFO: sem recurrência, mudar para a pasta de ignorar')
        shutil.move(filename, os.path.join(ignore_folder, filename))


# Função para atualizar a data de recorrência
def update_recurrence_date(config, filename):
    current_date = datetime.now()
    next_month = current_date.month + 1 if current_date.month < 12 else 1
    next_year = current_date.year if current_date.month < 12 else current_date.year + 1

    # Define o novo dia de envio
    new_date = datetime(next_year, next_month, config['recurrence_day'])
    config['next_send_date'] = new_date.strftime("%Y-%m-%d")  # Atualiza a data de envio
    # config['time_to_send'] = new_date.strftime("%H:%M")  # Mudar a hora original

    # Salva as novas configurações no arquivo
    with open(filename, 'w') as file:
        json.dump(config, file, indent=4, ensure_ascii=False)
    logging.info(f"Configuração atualizada para o próximo envio em: {new_date.strftime('%Y-%m-%d')}")


if __name__ == "__main__":
    if __name__ == "__main__":
        # Diretório raiz
        base_dir = os.getcwd()
        # Diretórios pais
        config_folder = load_config('config/config.json')
        email_folder = os.path.join(base_dir, 'trabalhos')
        # Diretórios intermediários
        ignore_folder = os.path.join(email_folder, 'ignorar')
        contacts_folder = os.path.join(email_folder, 'contactos')
        processed_folder = os.path.join(email_folder, 'processados')

        # Garantir que as pastas existem
        os.makedirs(email_folder, exist_ok=True)
        os.makedirs(ignore_folder, exist_ok=True)
        os.makedirs(contacts_folder, exist_ok=True)
        os.makedirs(processed_folder, exist_ok=True)

        # Arquivo para registrar arquivos processados
        processed_log_file = os.path.join(processed_folder, 'processed_files.log')

        # Garantir que log de hash existe
        if not os.path.exists(processed_log_file):
            open(processed_log_file, 'w').close()


        # Função para carregar hashes de arquivos processados
        def load_processed_hashes():
            if os.path.exists(processed_log_file):
                with open(processed_log_file, 'r') as file:
                    return {line.strip() for line in file}
            return set()


        # Função para registrar hashes de arquivos processados
        def log_processed_hash(file_hash):
            with open(processed_log_file, 'a') as file:
                file.write(f"{file_hash}\n")


        processed_hashes = load_processed_hashes()

        while True:
            # Verifica se há arquivos JSON na pasta de e-mails
            for trabalho in os.listdir(email_folder):
                if trabalho.endswith('.json'):
                    trabalho_corrente = os.path.join(email_folder, trabalho)
                    trabalho_config = load_config(trabalho_corrente)

                    # Verifica se a data de envio é hoje
                    if 'next_send_date' in trabalho_config:
                        next_send_date = datetime.strptime(trabalho_config['next_send_date'], "%Y-%m-%d")
                        current_date = datetime.now()

                        if next_send_date.date() == current_date.date():
                            # Verifica se a hora de envio é a correta
                            if 'time_to_send' in trabalho_config:
                                send_time = datetime.strptime(trabalho_config['time_to_send'], "%H:%M").time()
                                current_time = datetime.now().time()

                                if current_time >= send_time:  # Verifica se a hora atual é igual ou posterior à hora de envio
                                    # Calcula o hash do arquivo
                                    file_hash = calculate_file_hash(trabalho_corrente)

                                    # Verifica se o hash já foi processado hoje
                                    if file_hash not in processed_hashes:

                                        send_email(trabalho_config, config_folder, trabalho_corrente)

                                        # Regista o hash como processado
                                        log_processed_hash(file_hash)
                                        # Adiciona à lista de hashes processados
                                        processed_hashes.add(file_hash)
