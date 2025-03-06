import shutil
import smtplib
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
from business_logic import update_recurrence_date
from config import load_config
from utils import send_email
from utils import calculate_file_hash

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



                                send_email(email_config=trabalho_config,
                                           config=config_folder, filename=trabalho_corrente,
                                           contacts_folder=contacts_folder, ignore_folder=ignore_folder)

                                # Regista o hash como processado
                                log_processed_hash(file_hash)
                                # Adiciona à lista de hashes processados
                                processed_hashes.add(file_hash)
                            else:
                                logging.info(f"Ficheiro {trabalho}, com a hash {file_hash} já foi processado anteriormente. Mudar para igonrados")
                                shutil.move(trabalho_corrente, os.path.join(ignore_folder, trabalho))