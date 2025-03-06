import json
import logging

#Função para carregar configurações do arquivo JSON
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