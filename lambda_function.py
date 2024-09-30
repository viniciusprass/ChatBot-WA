import json
import requests
from datetime import datetime
import boto3
import ast
import random

# Configuração da API OpenAI e WhatsApp
api_key_gpt = 'x'
api_key_wpp = 'y'

dynamodb = boto3.resource('dynamodb')
table_context = dynamodb.Table('context')
table_appointments = dynamodb.Table('appointments')

def sendMessage(message, number):
    url = "https://graph.facebook.com/v20.0/z/messages"
    
    headers = {
        'Authorization': f'Bearer {api_key_wpp}',
        'Content-Type': 'application/json'
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": number,  
        "type": "text",
        "text": {
            "body": message
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    # print(response.status_code)
    # print(response.text)
    return response

def assistMessage(messages):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key_gpt}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": messages
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        result = response.json()
        return result['choices'][0]['message']['content']
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return

def lambda_handler(event, context):

    http_method = event.get('requestContext', {}).get('httpMethod')
    body = json.loads(event.get('body', '{}'))

    if not http_method:
        return {
            'statusCode': 400,
            'body': 'Método HTTP não especificado.'
        }
    
    if http_method == 'GET':
        query_params = event.get('queryStringParameters', {})
        if query_params.get('hub.mode') == 'subscribe' and query_params.get('hub.verify_token') == 'a':
            return {
                'statusCode': 200,
                'body': query_params.get('hub.challenge', '')
            }
        return {
            'statusCode': 403,
            'body': 'Token de verificação inválido'
        }

    if http_method == 'POST':
        entries = body.get('entry', [])
        if entries:
            changes = entries[0].get('changes', [])
            if changes:
                value = changes[0].get('value', {})
                messages = value.get('messages', [])
                if messages:
                    message = messages[0]
                    sender = message.get('from', 'Sem remetente')
                    user_message = message.get('text', {}).get('body', 'Sem texto')
                    if user_message:
                        context_data = table_context.get_item(Key={'id': sender})
                        conversation_history = context_data.get('Item', {}).get('conversation_history', [])
                        
                        responseTable = table_appointments.scan()
                        items = responseTable.get('Items', [])
                        codes = [item['id'] for item in items]
                        print(codes)
                        busySchedules = [item['data'] for item in items]
                        print(busySchedules)
                        
                        conversation_history.append({"role": "user", "content": user_message})
                        
                        assistantName = 'Assistente Inteligente WA'
                        today = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                        mensagens = [
                            {
                                "role": "system",
                                "content": f"""Você é o assistente virtual da WA Mobile Oil Change. Seu nome é {assistantName}. Sua função é auxiliar os clientes em agendar serviços de manutenção automotiva que a WA oferece, bem como responder a dúvidas sobre esses serviços.
                                
                                Este é o histórico das mensagens anteriores: {conversation_history}

                                A empresa opera a partir de uma van que vai até o local do cliente, sem custos adicionais de deslocamento. Os serviços oferecidos incluem: troca de óleo, troca de filtro de ar, troca de filtro de óleo, troca de fluido de arrefecimento, troca de pastilhas de freio, troca de limpadores de para-brisa e troca de bateria. 
                                
                                Na troca de óleo, o cliente ganha gratuitamente a troca do fluido de arrefecimento, a troca do líquido do limpador de para-brisa, além da revisão dos limpadores, pneus, bateria e pastilhas de freio. 
                                
                                Os agendamentos podem ser feitos de segunda a sábado, 24 horas por dia, no fuso horário da Flórida. 
                                
                                ### Valores de Troca de Óleo:
                                - **Uso Doméstico**:
                                  - 5QTZ = USD75
                                  - 6QTZ = USD80
                                  - 7QTZ = USD85
                                  - 8QTZ = USD93
                                  - DIESEL 13QTZ = USD138
                                - **Frotas**:
                                  - 5QTZ = USD60
                                  - 6QTZ = USD68
                                  - 7QTZ = USD75
                                  - 8QTZ = USD83
                                  - DIESEL 13QTZ = USD128
                                
                                ### Valores dos Serviços Adicionais (Válidos para todos os clientes):
                                - Filtro de ar = USD20
                                - Bateria = USD60
                                - Troca de limpadores de para-brisa = USD10
                                - Troca de pneu furado = USD30
                                - Rotação de pneus = USD40
                                - Troca de pastilhas de freio (dianteira ou traseira) = USD70
                                - Troca de pastilhas de freio (dianteira e traseira) = USD140
                                
                                ### Procedimento de Agendamento:
                                    Pergunte ao cliente (Não mande um bloco inteiro com todas as perguntas, questione apenas uma delas):
                                        - Nome completo
                                        - Endereço completo (rua, bairro e cidade; se for fora de Orlando, informe que não atendemos fora da área)
                                        - Modelo do carro em que o serviço será realizado
                                        - Data desejada para a visita (Esta é a lista dos horários indisponíveis: {busySchedules})
                                        - Questione se o serviço é doméstico ou para frotas de forma objetiva
                                        - Todas essas informações são obrigatórias.
                                   
                                    Calcule automaticamente o valor da troca de óleo com base no modelo do carro e informe o valor estimado ao cliente.
                                
                                    Após coletar as informações, confirme os detalhes do agendamento e o valor total com o cliente. Peça ao cliente para digitar 'confirmar' (em português) ou 'confirm' (em inglês) para finalizar o agendamento.
                                
                                ### Procedimento de Cancelamento:
                                - Se o cliente desejar excluir um agendamento, solicite o código fornecido no ato do agendamento. Verifique se o código está na lista: {codes}.
                                - Se o código for inválido, informe o cliente. Se for válido, peça que o cliente digite 'excluir' (em português) ou 'remove' (em inglês) para confirmar o cancelamento.
                                
                                Responda apenas a dúvidas sobre serviços mecânicos e sobre nossa empresa. Considere que hoje é {today}.
                                Não informe a lista de códigos ao cliente, são confidenciais.
                                Não informe os horários já agendados ao cliente, a não ser que ele pergunte.
                                Seja direto e objetivo."""

                            },
                            {"role": "user", "content": user_message}
                        ]
                        
                        def generate_unique_code():
                            while True:
                                code = str(random.randint(100000, 999999))
                                response = table_appointments.get_item(Key={'id': code})
                                if 'Item' not in response:
                                    return code
                        
                        def removeAppointment():
                            mensagens.append({
                                "role": "system", 
                                "content": f"verifique o código informado neste histórico: {conversation_history}, e me informe o código informado pelo cliente. Apenas o código, sem mais nada"
                            })
                            codeToRemove = assistMessage(mensagens)
                            print(codeToRemove)
                            table_appointments.delete_item(Key={'id': codeToRemove})
                            table_context.delete_item(Key={'id': sender})
                            sendMessage('Seu agendamento foi excluido com sucesso!\n\nCaso precise de mais alguma coisa, estou aqui para ajudar.', sender)
                        
                        def collectingData():
                            
                            code = generate_unique_code()
                            
                            mensagens.append({
                                "role": "system", 
                                "content": f"Caso tenha sido enviada para confirmação a visita, me retorne os dados informados neste formato: {{'servico': a, 'nome': x, 'modelo': z, 'uso': a, 'localizacao': b, 'data': 'dia/mes/ano das (hora)h às (hora+1)h'}}. Onde 'modelo' é o modelo do carro, o 'uso' é se é doméstico ou de frota e o 'servico' é o serviço a ser prestado (exemplo: 'troca de óleo'), mande apenas o dicionário limpo, sem mais informações. Se não conseguir coletar, retorne 'unconfirmed'."
                            })
                        
                            data = assistMessage(mensagens)
                            
                            print(f'Dados: {data}')
                            
                            if data == 'unconfirmed':
                                sendMessage(f'Ainda faltam dados a serem coletados.', sender)
                                return
                            
                            try:
                                dictionaryData = ast.literal_eval(data)
                            except (ValueError, SyntaxError):
                                return
                            
                            table_appointments.put_item(
                                Item={
                                    'id': code,
                                    'servico': dictionaryData['servico'],
                                    'nome': dictionaryData['nome'],
                                    'telefone': sender,
                                    'modelo': dictionaryData['modelo'],
                                    'uso': dictionaryData['uso'],
                                    'localizacao': dictionaryData['localizacao'],
                                    'data': dictionaryData['data']
                                }
                            )
                            sendMessage(f'Seu código de agendamento é: {code}. \n\nA solicitação de agendamento foi enviada para aprovação e você receberá a confirmação em breve. \n\nSe precisar de mais alguma coisa, estarei à disposição!', sender)
                            table_context.delete_item(Key={'id': sender})

                        if user_message.lower() == 'confirmar' or user_message.lower() == 'confirm':
                            collectingData()
                        
                        elif user_message.lower() == 'excluir' or user_message.lower() == 'remove':
                            removeAppointment()
                            
                        else:
                            resposta = assistMessage(mensagens)
                            
                            conversation_history.append({"role": "assistant", "content": resposta})
                            table_context.put_item(
                                Item={
                                    'id': sender,
                                    'conversation_history': conversation_history
                                }
                            )
                            
                            sendMessage(resposta, sender)

                        return {
                            'statusCode': 200,
                        }               
                else:
                    print("Nenhuma mensagem encontrada no corpo do evento.")

        return {
            'statusCode': 400,
            'body': 'Evento POST malformado.'
        }

    return {
        'statusCode': 405,
        'body': json.dumps({'message': 'Method not allowed'})
    }
