import logging
import json
from datetime import datetime


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