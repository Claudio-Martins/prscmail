import os
import shutil
import time
import hashlib
import re
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from business_logic import update_recurrence_date
from pathlib import Path


def calculate_file_hash(filename):
    """Calcula o hash MD5 do conteúdo do arquivo."""
    hash_md5 = hashlib.md5()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


# Função para validar a estrutura básica de um endereço
def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


# Função para carregar contactos a partir de txt
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
def send_email(email_config, config, filename, contacts_folder, ignore_folder):
    print('#', ignore_folder)
    ignore_folder = Path(ignore_folder)
    print('##', ignore_folder)

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
            logging.error(f"ao enviar e-mail para {to_email}: {e}")
            if attempt < max_retries - 1:
                logging.info(f"Tentar novamente em 5 segundos... (Tentativa {attempt + 2}/{max_retries})")
                time.sleep(5)  # Esperar antes de enviar
            else:
                logging.error(f"Falha ao enviar e-mail para {to_email} após {max_retries} tentativas.")
                return  # Sair depois de tentativas esgotadas

    # Atualiza a data de envio se a recorrência estiver definida
    if isinstance(email_config["recurrence_day"], int):
        logging.info(f'encontrada recurrência para dia {email_config["recurrence_day"]} do próximo mês')
        update_recurrence_date(email_config, filename)
    else:
        logging.info('sem recurrência, mudar para a pasta de ignorar')
        shutil.move(str(filename), os.path.join(Path(ignore_folder), Path(filename).stem))